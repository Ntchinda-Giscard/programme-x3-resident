from calendar import c
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from pathlib import Path
import smtplib
from typing import Any, Dict, List, Optional
import zipfile
import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import logging
import pyodbc
import sqlite3
from datetime import datetime
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.FileHandler('fastapi.log')
    ]
)
logger = logging.getLogger(__name__)

BASE_FOLDER = r"C:\poswaza\temp"
LOCAL_DB_PATH = rf"{BASE_FOLDER}\db"
ZIP_FOLDER = rf"{BASE_FOLDER}\zip"
DELTA_FOLDER = rf"{BASE_FOLDER}\delta"

class DatabaseSync:
    def __init__(
        self, 
        sql_server_config: Dict[str, str],
        tables_to_sync: List[str],
        email_config: Optional[Dict[str, str]],
        parameters: Optional[Dict[str, Any]],
        local_db_path: str,
        zip_folder: str = ZIP_FOLDER,
        fs: Optional[Any] = None
    ):
        """
        Initialize the sync manager.
        
        :param sql_server_config: Dictionary containing SQL Server connection details
        :param local_db_path: Path to the local SQLite database
        :param zip_folder: Folder where the zipped database will be saved
        :param email_config: Optional email configuration for sending the zip file
        """
        self.sql_config = sql_server_config
        self.parameters = parameters
        self.zip_folder = zip_folder
        self.email_config = email_config
        self.fs = fs
        self.tables_to_sync = tables_to_sync
        
        # Create folders if they don't exist
        Path(self.zip_folder).mkdir(parents=True, exist_ok=True)
        Path(DELTA_FOLDER).mkdir(parents=True, exist_ok=True)
        os.makedirs(LOCAL_DB_PATH, exist_ok=True)
        
        # Initialize local tracking table
        # self._init_local_db()
        
        #  Initialize first launch flag
        self._init_first_launch(self.tables_to_sync)

    def _get_sql_connection(self):
        """Creates a connection to the remote SQL Server using DSN or Windows Auth."""
        dsn = self.sql_config.get('dsn')
        username = self.sql_config.get('username')
        password = self.sql_config.get('password')
        
        if dsn:
            if username and password:
                conn_str = f"DSN={dsn};UID={username};PWD={password}"
            else:
                conn_str = f"DSN={dsn};Trusted_Connection=yes"
        else:
            server = self.sql_config.get('server')
            database = self.sql_config.get('database')
            driver = self.sql_config.get('driver', 'ODBC Driver 17 for SQL Server')
            
            if username and password:
                conn_str = (
                    f"DRIVER={{{driver}}};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"UID={username};"
                    f"PWD={password}"
                )
            else:
                conn_str = (
                    f"DRIVER={{{driver}}};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"Trusted_Connection=yes"
                )
        
        if self.fs:
            self.fs.write(f"[*] Connecting with: {conn_str.replace(password or '', '***') if password else conn_str}\n")
        
        conn = pyodbc.connect(conn_str, timeout=30)
        
        # Use latin-1 encoding to handle Windows-specific characters
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='latin-1')
        conn.setdecoding(pyodbc.SQL_WCHAR, encoding='latin-1')
        conn.setencoding('latin-1')
        
        return conn





    def _init_first_launch(self, tables: List[str]):

        for site in self.parameters["sites"]: # type: ignore
            if self.fs:
                self.fs.write(f"[*] Exporting tables for site: {site}\n")
            self.ensure_folder(rf"{LOCAL_DB_PATH}\{site}")
            sqlite_path = rf"{LOCAL_DB_PATH}\{site}\local_data.db"
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_cur = sqlite_conn.cursor()

            with self._get_sql_connection() as conn:
                sql_cursor = conn.cursor()
                
                for table in tables:
                    # Determine full table name based on site dependency
                    full_table = f"{self.sql_config['schema']}.{table}" # type: ignore

                    if table in self.parameters["site_dependent_tables"]: # type: ignore
                        if self.fs:
                            self.fs.write(f"[*] Exporting site-dependent table {table} for site {site} to local DB...\n")
                        
                        query = f"SELECT * FROM {full_table} WHERE {self.parameters['keys_columns'][table]} = ?" # type: ignore
                        sql_cursor.execute(query, (site,))
                        
                    elif table in self.parameters["all_tables"]: # type: ignore
                        if self.fs:
                            self.fs.write(f"[*] Exporting table {table} to local DB...\n")

                        query = f"SELECT * FROM {full_table}"
                        sql_cursor.execute(query)
                    

                    # Fetch column definitions from SQL Server
                    columns = [column[0] for column in sql_cursor.description]

                    # Create table in SQLite
                    columns_def = ", ".join([f'"{col}" TEXT' for col in columns])  # TEXT default
                    sqlite_cur.execute(f"DROP TABLE IF EXISTS {table}")
                    sqlite_cur.execute(f"CREATE TABLE {table} ({columns_def})")

                    # Fetch all data
                    rows = sql_cursor.fetchall()
                    placeholders = ", ".join(["?"] * len(columns))
                    insert_query = f"INSERT INTO {table} VALUES ({placeholders})"

                    # Insert into SQLite
                    for row in rows:
                        sqlite_cur.execute(insert_query, tuple(str(x) if x is not None else None for x in row))
                    
                    if len(rows) > 0 and self.fs:
                        self.fs.write(f"    Inserted {len(rows)} records into {table}.\n")

                        pk_column = self.parameters.get("keys_columns", {}) # type: ignore
                        pk_indexes = columns.index(pk_column)
                        pk_values = [row[pk_indexes] for row in rows]

                        # Build dynamic placeholder list for IN (...)
                        placeholders = ",".join("?" for _ in pk_values)

                        update_sql = f"""
                            UPDATE {full_table}
                            SET 
                                ZTRANSFERT_0 = 2,
                                ZTRANSDATE_0 = GETDATE()
                            WHERE {pk_column} IN ({placeholders})
                        """

                        sql_cursor.execute(update_sql, pk_values)
                        conn.commit()

                        if self.fs:
                            self.fs.write(
                                f"[*] Updated {len(pk_values)} exported rows in {table} "
                                f"(ZTRANSFERT_0=2, ZTRANSTDATE_0=NOW)\n"
                            )

                sqlite_conn.commit()

                if self.fs:
                    self.fs.write(f"[*] Export completed. Local DB path: {sqlite_path}\n")
            
            if self.fs:
                self.fs.write(f"[*] Exported tables to local DB at {sqlite_path}\n")
            
            sqlite_conn.close()
            conn.close()

    def ensure_folder(self, path):
        os.makedirs(path, exist_ok=True)
        return path

    def send_email(self, zip_path: str, is_first_sync: bool):
        """
        Sends the zipped file via email with appropriate subject.
        """
        if not self.email_config:
            if self.fs:
                self.fs.write("    No email configuration provided, skipping email.\n")
            return
        
        sync_type = "FULL DATABASE" if is_first_sync else "DELTA RECORDS"
        if self.fs:
            self.fs.write(f"[*] Sending email with {sync_type} to {self.email_config['to_email']}...\n")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            msg['Subject'] = f"{sync_type} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            body_text = f"{sync_type} sync completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            if is_first_sync:
                body_text += "This is a full database backup containing all records.\n"
            else:
                body_text += "This contains only the changed/new records since last sync.\n"
            
            msg.attach(MIMEText(body_text, 'plain'))
            
            with open(zip_path, 'rb') as attachment:
                part = MIMEBase('application', 'zip')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(zip_path)}')
                msg.attach(part)
            
            smtp_server = self.email_config['smtp_server']
            smtp_port = int(self.email_config.get('smtp_port', 587))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if 'smtp_username' in self.email_config and 'smtp_password' in self.email_config:
                    server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])
                server.send_message(msg)
            
            if self.fs:
                self.fs.write(f"    Email sent successfully!\n")
        except Exception as e:
            if self.fs:
                self.fs.write(f"    Error sending email: {e}\n")

    def run_sync(self, tables_to_sync: List[tuple]):
        """
        Runs the sync process for all specified tables.
        
        - LOCAL DB: Always does UPSERT (adds/updates records, never recreates)
        - EMAIL: First sync sends full DB, subsequent syncs send only changed records
        
        :param tables_to_sync: List of tuples (table_name, pk_column, timestamp_column)
                                or (table_name, pk_column, timestamp_column, schema)
        """
        
        if self.fs:
            self.fs.write("\n[*] No changes detected. Skipping backup.\n")


class PythonService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WAZAPOS_TEST"
    _svc_display_name_ = "WAZAPOS_TEST"
    _svc_description_ = "Syncs SQL Server data to local SQLite and emails backups"
    
    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        """Called when the service is stopped."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        """Main service loop."""
        servicemanager.LogInfoMsg("WAZAPOS_TEST - Starting service...")
        
        BASE_FOLDER = r"C:\poswaza\temp"
        LOCAL_DB_PATH = rf"{BASE_FOLDER}\db"
        ZIP_FOLDER = rf"{BASE_FOLDER}\zip"
        log_folder = rf"{BASE_FOLDER}\logs"
        
        os.makedirs(LOCAL_DB_PATH, exist_ok=True)
        os.makedirs(ZIP_FOLDER, exist_ok=True)
        os.makedirs(log_folder, exist_ok=True)
        
        
        tables_to_sync = [
                        "ITMMASTER",
                        "ITMFACILIT", "FACILITY",
                        "ITMSALES",
                        "BPARTNER",
                        "BPCUSTOMER",
                        "BPCUSTMVT",
                        "BPDLVCUST",
                        "SALESREP",
                        "SPRICLINK",
                        "PRICSTRUCT",
                        "SPREASON",
                        "SPRICCONF",
                        "SPRICLIST",
                        "SORDER",
                        "PIMPL",
                        "TABMODELIV",
                        "STOCK",
                        "BPCARRIER",
                        "COMPANY",
                        "TABSOHTYP",
                        "TABVACBPR",
                        "SVCRVAT",
                        "ITMCATEG",
                        "CBLOB",
                        "ABLOB",
                        "AUTILIS",
                        "AMENUSER",
                        "TABVAT",
                        "BPADDRESS",
                        "WAREHOUSE",
                        "TABPAYTERM",
                        "TABDEPAGIO",
                        "BPCINVVAT",
                        "TABRATVAT",
                        "TABVACITM",
                        "TABVAC",
                        "TAXLINK",
                        "SFOOTINV",
                        "SORDERQ",
                        "SORDERP"
                    ]
        
        
        with open(rf"{log_folder}\service_log.txt", "a") as f:
            try:
                db_path = rf"{LOCAL_DB_PATH}\config.db"
                config_conn = sqlite3.connect(db_path)
                config_cursor = config_conn.cursor()
                config_cursor.execute("SELECT * FROM database_configuration")
                config_rows = config_cursor.fetchone()
                config_conn.close()
                
                sql_config = {
                    'username': config_rows[7],
                    'password': config_rows[8],
                    'server': f"{config_rows[3]},{config_rows[4]}",
                    'database': config_rows[5],
                    'driver': 'ODBC Driver 17 for SQL Server',
                    'dsn': config_rows[1],
                    'schema': config_rows[6]
                }
                            
                # Get folder configuration
                folder_conn = sqlite3.connect(db_path)
                folder_cursor = folder_conn.cursor()
                folder_cursor.execute("SELECT * FROM configurations_folders")
                folder_rows = folder_cursor.fetchone()
                folder_conn.close()
                            
                # Get email configuration
                email_conn = sqlite3.connect(db_path)
                email_cursor = email_conn.cursor()
                email_cursor.execute("SELECT * FROM email_configs")
                email_rows = email_cursor.fetchone()
                email_conn.close()
                            
                email_config = {
                    'smtp_server': email_rows[1],
                    'smtp_port': email_rows[4],
                    'smtp_username': email_rows[2],
                    'smtp_password': email_rows[3],
                    'from_email': email_rows[2],
                    'to_email': email_rows[5],
                    'subject': 'Database Sync Update'
                }
                parameters = {
                        "sites": ["AE011", "AE012"],
                        "site_dependent_tables": ["ITMFACILIT","FACILITY"],
                        "keys_columns": {"ITMFACILIT": "STOFCY_0", "FACILITY": "FCY_0"},
                        "keys_columns" :  "AUUID_0", 
                        "all_tables": tables_to_sync
                    }
        
                syncer = DatabaseSync(
                            sql_config,
                            tables_to_sync=tables_to_sync,
                            local_db_path=rf"{LOCAL_DB_PATH}",
                            zip_folder=ZIP_FOLDER,
                            email_config=email_config,
                            parameters = parameters,
                            fs=f
                        )
            except Exception as e:
                    f.write(f"Error in service execution: {e}\n")
        while self.running:
            with open(rf"{log_folder}\service_log.txt", "a") as f:
                try:
                    f.write(f"\n--- Sync run at {datetime.now()} ---\n")
                                        
                    f.write(f"Next sync in 60 seconds...\n")
                    time.sleep(60)
                    
                except Exception as e:
                    f.write(f"Error in service execution: {e}\n")
            
            time.sleep(60)

        servicemanager.LogInfoMsg("WAZAPOS_TEST - Service stopped.")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)

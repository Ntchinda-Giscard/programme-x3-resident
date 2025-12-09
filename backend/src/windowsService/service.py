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
import csv

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

                    # First, check if table has tracking columns
                    check_columns_query = f"SELECT TOP 1 * FROM {full_table}"
                    sql_cursor.execute(check_columns_query)
                    columns = [column[0] for column in sql_cursor.description]
                    has_tracking = 'ZTRANSFERT_0' in columns and 'ZTRANSDATE_0' in columns

                    # Determine the primary key column
                    if table in self.parameters["site_dependent_tables"]: # type: ignore
                        pk_column = self.parameters['site_keys_column'][table] # type: ignore
                    else:
                        pk_column = self.parameters["primary_key_column"] # type: ignore

                    # **STEP 1: UPDATE SQL SERVER FIRST (if has tracking columns)**
                    if has_tracking and pk_column in columns:
                        if self.fs:
                            self.fs.write(f"[*] Updating tracking columns in SQL Server for {table}...\n")
                        
                        # Get list of primary keys to update
                        if table in self.parameters["site_dependent_tables"]: # type: ignore
                            pk_query = f"SELECT {pk_column} FROM {full_table} WHERE {self.parameters['site_keys_column'][table]} = ?" # type: ignore
                            sql_cursor.execute(pk_query, (site,))
                        else:
                            pk_query = f"SELECT {pk_column} FROM {full_table}"
                            sql_cursor.execute(pk_query)
                        
                        pk_values = [row[0] for row in sql_cursor.fetchall()]
                        
                        if len(pk_values) > 0:
                            # Update in batches to avoid parameter limit
                            batch_size = 1000
                            total_updated = 0
                            
                            for i in range(0, len(pk_values), batch_size):
                                batch = pk_values[i:i + batch_size]
                                placeholders_batch = ",".join("?" for _ in batch)

                                update_sql = f"""
                                    UPDATE {full_table}
                                    SET 
                                        ZTRANSFERT_0 = 2,
                                        ZTRANSDATE_0 = GETDATE()
                                    WHERE {pk_column} IN ({placeholders_batch})
                                """
                                sql_cursor.execute(update_sql, batch)
                                conn.commit()
                                total_updated += len(batch)
                            
                            if self.fs:
                                self.fs.write(f"    Updated {total_updated} rows in SQL Server (in {(len(pk_values) + batch_size - 1) // batch_size} batches)\n")

                    # **STEP 2: NOW FETCH THE UPDATED DATA**
                    if table in self.parameters["site_dependent_tables"]: # type: ignore
                        if self.fs:
                            self.fs.write(f"[*] Exporting site-dependent table {table} for site {site} to local DB...\n")
                        
                        query = f"SELECT * FROM {full_table} WHERE {self.parameters['site_keys_column'][table]} = ?" # type: ignore
                        sql_cursor.execute(query, (site,))
                        
                    else:
                        if self.fs:
                            self.fs.write(f"[*] Exporting table {table} to local DB...\n")

                        query = f"SELECT * FROM {full_table}"
                        sql_cursor.execute(query)
                    
                    # Fetch column definitions from SQL Server
                    columns = [column[0] for column in sql_cursor.description]

                    # Create table in SQLite
                    columns_def = ", ".join([f'"{col}" TEXT' for col in columns])
                    sqlite_cur.execute(f"DROP TABLE IF EXISTS {table}")
                    sqlite_cur.execute(f"CREATE TABLE {table} ({columns_def})")

                    # Fetch all data (now with updated values!)
                    rows = sql_cursor.fetchall()
                    
                    if len(rows) > 0:
                        placeholders = ", ".join(["?"] * len(columns))
                        insert_query = f"INSERT INTO {table} VALUES ({placeholders})"

                        # Insert into SQLite
                        for row in rows:
                            sqlite_cur.execute(insert_query, tuple(str(x) if x is not None else None for x in row))
                        
                        if self.fs:
                            self.fs.write(f"    Inserted {len(rows)} records into {table} (SQLite).\n")
                    else:
                        if self.fs:
                            self.fs.write(f"    No records found for {table}.\n")
                
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

    def run_sync(self):
        """
        Monitors SQL Server tables for changes and sends a single consolidated CSV per site.
        
        Logic:
        - ZTRANSFERT_0 = 0: New record (never transferred)
        - ZTRANSFERT_0 = 2 AND UPDDATTIM_0 > ZTRANSDATE_0: Updated record
        
        Creates one CSV file per site containing:
        - All generic (non-site) tables with changes
        - Site-specific tables with changes for that site
        """
        
        if self.fs:
            self.fs.write(f"\n[*] Starting sync monitoring at {datetime.now()}\n")
        
        # Get email addresses for each site
        site_emails = self.parameters.get("site_emails", {}) # type: ignore
        
        if not site_emails:
            if self.fs:
                self.fs.write("[!] No site emails configured. Skipping sync.\n")
            return
        
        with self._get_sql_connection() as conn:
            sql_cursor = conn.cursor()
            
            # Collect all changes per site
            site_changes = {}  # {site: {table: (columns, rows)}}
            generic_changes = {}  # {table: (columns, rows)} - for non-site tables
            
            for table in self.tables_to_sync:
                full_table = f"{self.sql_config['schema']}.{table}"
                
                # Check if table has tracking columns
                check_query = f"SELECT TOP 1 * FROM {full_table}"
                sql_cursor.execute(check_query)
                columns = [column[0] for column in sql_cursor.description]
                
                has_tracking = (
                    'ZTRANSFERT_0' in columns and 
                    'ZTRANSDATE_0' in columns and 
                    'UPDDATTIM_0' in columns
                )
                
                if not has_tracking:
                    if self.fs:
                        self.fs.write(f"[*] Table {table} does not have tracking columns. Skipping.\n")
                    continue
                
                # Determine if site-dependent
                is_site_dependent = table in self.parameters.get("site_dependent_tables", []) # type: ignore
                
                if is_site_dependent:
                    # Collect changes per site
                    site_column = self.parameters['site_keys_column'].get(table) # type: ignore
                    if not site_column:
                        if self.fs:
                            self.fs.write(f"[!] No site column defined for {table}. Skipping.\n")
                        continue
                    
                    for site in self.parameters.get("sites", []): # type: ignore
                        query = f"""
                            SELECT * FROM {full_table}
                            WHERE {site_column} = ?
                            AND (
                                ZTRANSFERT_0 = 0 
                                OR (ZTRANSFERT_0 = 2 AND UPDDATTIM_0 > ZTRANSDATE_0)
                            )
                        """
                        
                        sql_cursor.execute(query, (site,))
                        rows = sql_cursor.fetchall()
                        
                        if len(rows) > 0:
                            if self.fs:
                                self.fs.write(f"[*] Found {len(rows)} changed records in {table} for site {site}\n")
                            
                            if site not in site_changes:
                                site_changes[site] = {}
                            site_changes[site][table] = (columns, rows)
                            
                            # Update tracking columns
                            self._update_tracking_columns(conn, sql_cursor, table, full_table, columns, rows)
                
                else:
                    # Generic table - collect changes once
                    query = f"""
                        SELECT * FROM {full_table}
                        WHERE 
                            ZTRANSFERT_0 = 0 
                            OR (ZTRANSFERT_0 = 2 AND UPDDATTIM_0 > ZTRANSDATE_0)
                    """
                    
                    sql_cursor.execute(query)
                    rows = sql_cursor.fetchall()
                    
                    if len(rows) > 0:
                        if self.fs:
                            self.fs.write(f"[*] Found {len(rows)} changed records in {table} (generic table)\n")
                        
                        generic_changes[table] = (columns, rows)
                        
                        # Update tracking columns
                        self._update_tracking_columns(conn, sql_cursor, table, full_table, columns, rows)
            
            # Now create one CSV per site with all their changes
            for site in self.parameters.get("sites", []): # type: ignore
                email = site_emails.get(site)
                if not email:
                    if self.fs:
                        self.fs.write(f"[!] No email configured for site {site}. Skipping.\n")
                    continue
                
                # Combine generic changes + site-specific changes
                all_changes_for_site = {}
                
                # Add generic tables
                for table, (columns, rows) in generic_changes.items():
                    all_changes_for_site[table] = (columns, rows)
                
                # Add site-specific tables
                if site in site_changes:
                    for table, (columns, rows) in site_changes[site].items():
                        all_changes_for_site[table] = (columns, rows)
                
                # Only send email if there are changes
                if len(all_changes_for_site) > 0:
                    csv_path = self._export_consolidated_csv(all_changes_for_site, site)
                    self._send_consolidated_email(csv_path, site, email, all_changes_for_site)
                else:
                    if self.fs:
                        self.fs.write(f"[*] No changes for site {site}\n")
        
        if self.fs:
            self.fs.write(f"[*] Sync monitoring completed at {datetime.now()}\n")

    def _export_consolidated_csv(self, changes_dict, site):
        """
        Export all changes to a single consolidated CSV file.
        
        Format:
        TABLE_NAME,column1,column2,column3,...
        ITMMASTER,value1,value2,value3,...
        ITMMASTER,value1,value2,value3,...
        FACILITY,value1,value2,...
        FACILITY,value1,value2,...
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"sync_{site}_{timestamp}.csv"
        csv_path = os.path.join(DELTA_FOLDER, csv_filename)
        
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            for table, (columns, rows) in changes_dict.items():
                # Write header row with table name as first column
                header = ['TABLE_NAME'] + columns
                writer.writerow(header)
                
                # Write data rows with table name prefixed
                for row in rows:
                    data_row = [table] + [str(x) if x is not None else '' for x in row]
                    writer.writerow(data_row)
        
        if self.fs:
            self.fs.write(f"    Exported consolidated CSV: {csv_path}\n")
        
        return csv_path

    def _send_consolidated_email(self, csv_path, site, to_email, changes_dict):
        """Send consolidated CSV file via email."""
        if not self.email_config:
            if self.fs:
                self.fs.write("    No email configuration provided, skipping email.\n")
            return
        
        # Calculate totals
        total_records = sum(len(rows) for _, (_, rows) in changes_dict.items())
        total_tables = len(changes_dict)
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = to_email
            msg['Subject'] = f"Database Sync - {site} - {total_tables} tables, {total_records} records - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Build detailed body
            body_text = f"""Database Sync Update
                    Site: {site}
                    Total Tables: {total_tables}
                    Total Records: {total_records}
                    Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

                    Tables included in this sync:
                    """
            
            for table, (_, rows) in changes_dict.items():
                body_text += f"  - {table}: {len(rows)} records\n"
            
            body_text += "\nThis file contains all new or updated records since the last sync.\n"
            
            msg.attach(MIMEText(body_text, 'plain'))
            
            # Attach CSV file
            with open(csv_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(csv_path)}')
                msg.attach(part)
            
            smtp_server = self.email_config['smtp_server']
            smtp_port = int(self.email_config.get('smtp_port', 587))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if 'smtp_username' in self.email_config and 'smtp_password' in self.email_config:
                    server.login(self.email_config['smtp_username'], self.email_config['smtp_password'])
                server.send_message(msg)
            
            if self.fs:
                self.fs.write(f"    Email sent to {to_email} ({total_tables} tables, {total_records} records)\n")
        except Exception as e:
            if self.fs:
                self.fs.write(f"    Error sending email to {to_email}: {e}\n")
   
    def _update_tracking_columns(self, conn, sql_cursor, table, full_table, columns, rows):
        """Update tracking columns after successful export."""
        
        # Determine primary key column
        if table in self.parameters.get("site_dependent_tables", []): # type: ignore
            pk_column = self.parameters['site_keys_column'].get(table) # type: ignore
        else:
            pk_column = self.parameters.get("primary_key_column", "AUUID_0") # type: ignore
        
        if pk_column not in columns:
            if self.fs:
                self.fs.write(f"    Warning: Primary key column '{pk_column}' not found. Skipping update.\n")
            return
        
        pk_index = columns.index(pk_column)
        pk_values = [row[pk_index] for row in rows]
        
        # Update in batches
        batch_size = 1000
        
        for i in range(0, len(pk_values), batch_size):
            batch = pk_values[i:i + batch_size]
            placeholders_batch = ",".join("?" for _ in batch)
            
            update_sql = f"""
                UPDATE {full_table}
                SET 
                    ZTRANSFERT_0 = 2,
                    ZTRANSDATE_0 = GETDATE()
                WHERE {pk_column} IN ({placeholders_batch})
            """
            
            sql_cursor.execute(update_sql, batch)
            conn.commit()
        
        if self.fs:
            self.fs.write(f"    Updated {len(pk_values)} records tracking columns\n")



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
                        "ITMFACILIT", 
                        "FACILITY",
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
                    "site_dependent_tables": ["ITMFACILIT", "FACILITY"],
                    "site_keys_column": {"ITMFACILIT": "STOFCY_0", "FACILITY": "FCY_0"},
                    "primary_key_column": "AUUID_0", 
                    "all_tables": [t for t in tables_to_sync if t not in ["ITMFACILIT", "FACILITY"]],  # Exclude site-dependent
                    "site_emails": {
                        "AE011": "angeldobaron@gmail.com",
                        "AE012": "chrisdobaron@gmail.com"
                    }  
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
                    syncer.fs = f  # type: ignore # Update file handle
                    syncer.run_sync() # type: ignore
                    time.sleep(60)
                    
                except Exception as e:
                    f.write(f"Error in service execution: {e}\n")
            
            time.sleep(60)

        servicemanager.LogInfoMsg("WAZAPOS_TEST - Service stopped.")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)

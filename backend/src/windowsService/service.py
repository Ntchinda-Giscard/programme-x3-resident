
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
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


# txdp zcoh ucum ezxt
# ntchinda1998@gmail.com
class DatabaseSync:
    def __init__(
        self, 
        sql_server_config: Dict[str, str], 
        local_db_path: str = rf"{LOCAL_DB_PATH}\local_data.db",
        zip_folder: str = ZIP_FOLDER,
        email_config: Optional[Dict[str, str]] = None,
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
        self.local_db_path = local_db_path
        self.zip_folder = zip_folder
        self.email_config = email_config
        self.fs = fs
        
        # Create zip folder if it doesn't exist
        Path(self.zip_folder).mkdir(parents=True, exist_ok=True)

        os.makedirs(LOCAL_DB_PATH, exist_ok=True)
        
        # Initialize local tracking table
        self._init_local_db()

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
        return pyodbc.connect(conn_str)

    def _get_local_connection(self):
        """Creates a connection to the local SQLite database."""
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_local_db(self):
        """Creates necessary metadata tables in local DB if they don't exist."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_state (
                    table_name TEXT PRIMARY KEY,
                    last_sync_timestamp DATETIME
                )
            """)
            conn.commit()

    def get_last_sync_time(self, table_name: str) -> datetime:
        """Retrieves the last successful sync timestamp for a table."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_sync_timestamp FROM sync_state WHERE table_name = ?", (table_name,))
            row = cursor.fetchone()
            
            if row and row['last_sync_timestamp']:
                return datetime.fromisoformat(row['last_sync_timestamp'])
            
            return datetime.min

    def update_sync_time(self, table_name: str, sync_time: datetime):
        """Updates the last sync timestamp."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sync_state (table_name, last_sync_timestamp)
                VALUES (?, ?)
            """, (table_name, sync_time.isoformat()))
            conn.commit()

    def ensure_local_table_exists(self, table_name: str, columns: List[tuple], pk_column: str):
        """
        Creates the local table if it doesn't exist, matching the source schema.
        Simple mapping: SQL Server types -> SQLite types (TEXT/NUMERIC/BLOB)
        
        :param table_name: Name of the table
        :param columns: List of (column_name, data_type) tuples
        :param pk_column: The actual primary key column name to use
        """
        seen_columns = set()
        unique_columns = []
        for col_name, data_type in columns:
            if col_name not in seen_columns:
                seen_columns.add(col_name)
                unique_columns.append((col_name, data_type))
        
        col_defs = []
        for col_name, data_type in unique_columns:
            if 'int' in data_type.lower():
                sqlite_type = 'INTEGER'
            elif 'char' in data_type.lower() or 'text' in data_type.lower() or 'date' in data_type.lower():
                sqlite_type = 'TEXT'
            elif 'decimal' in data_type.lower() or 'float' in data_type.lower() or 'money' in data_type.lower():
                sqlite_type = 'REAL'
            else:
                sqlite_type = 'TEXT'
            
            col_defs.append(f'"{col_name}" {sqlite_type}')

        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)}, PRIMARY KEY ("{pk_column}"))'
        
        with self._get_local_connection() as conn:
            conn.execute(create_sql)

    def sync_table(self, table_name: str, pk_column: str, timestamp_column: str, schema: str = "dbo") -> bool:
        """
        Synchronizes a specific table from SQL Server to Local DB.
        
        :param table_name: Name of the table to sync
        :param pk_column: Primary key column name (for upserts)
        :param timestamp_column: Column used to track changes (e.g., UpdatedAt, ModifiedDate)
        :param schema: Schema name (default: dbo) - IMPORTANT for avoiding duplicate columns
        :return: True if changes were made, False otherwise
        """
        if self.fs:
            self.fs.write(f"[*] Starting sync for table: {schema}.{table_name}\n")
        
        last_sync = self.get_last_sync_time(table_name)
        if self.fs:
            self.fs.write(f"    Last sync time: {last_sync}\n")
        try:
            sql_conn = self._get_sql_connection()
            sql_cursor = sql_conn.cursor()

            sql_cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ? AND TABLE_SCHEMA = ?
                ORDER BY ORDINAL_POSITION
            """, (table_name, schema))
            columns = [(row.COLUMN_NAME, row.DATA_TYPE) for row in sql_cursor.fetchall()]
            
            if not columns:
                if self.fs:
                    self.fs.write(f"    Warning: No columns found for {schema}.{table_name}, trying without schema filter...")
                sql_cursor.execute(f"""
                    SELECT DISTINCT COLUMN_NAME, DATA_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = ?
                    ORDER BY COLUMN_NAME
                """, (table_name,))
                columns = [(row.COLUMN_NAME, row.DATA_TYPE) for row in sql_cursor.fetchall()]
                
                if not columns:
                    if self.fs:
                        self.fs.write(f"    Error: Table {table_name} not found in SQL Server.\n")
                    return False

            self.ensure_local_table_exists(table_name, columns, pk_column)
            
            seen = set()
            unique_col_names = []
            for c in columns:
                if c[0] not in seen:
                    seen.add(c[0])
                    unique_col_names.append(c[0])
            
            placeholders = ','.join(['?' for _ in unique_col_names])
            cols_str = ','.join([f'"{c}"' for c in unique_col_names])

            query = f'SELECT {cols_str} FROM "{schema}"."{table_name}" WHERE "{timestamp_column}" > ?'
            sql_cursor.execute(query, last_sync)
            
            rows = sql_cursor.fetchall()
            
            if not rows:
                if self.fs:
                    self.fs.write("    No new changes found.\n")
                sql_conn.close()
                return False

            if self.fs:
                self.fs.write(f"    Found {len(rows)} records to update.")

            local_conn = self._get_local_connection()
            local_cursor = local_conn.cursor()
            
            new_max_date = last_sync

            local_cursor.execute("BEGIN TRANSACTION")
            try:
                for row in rows:
                    values = self._convert_row_for_sqlite(tuple(row))
                    
                    upsert_sql = f"""
                        INSERT OR REPLACE INTO "{table_name}" ({cols_str})
                        VALUES ({placeholders})
                    """
                    local_cursor.execute(upsert_sql, values)
                    
                    # Find the index of timestamp column
                    try:
                        ts_index = unique_col_names.index(timestamp_column)
                        row_date = values[ts_index]
                    except (ValueError, IndexError):
                        row_date = getattr(row, timestamp_column, None)
                    
                    if row_date:
                        if isinstance(row_date, str):
                            try:
                                row_date = datetime.fromisoformat(row_date)
                            except ValueError:
                                pass
                                
                        if isinstance(row_date, datetime) and row_date > new_max_date:
                            new_max_date = row_date

                local_conn.commit()
                
                self.update_sync_time(table_name, new_max_date)
                if self.fs:
                    self.fs.write(f"    Successfully synced. New watermark: {new_max_date}\n")
                
            except Exception as e:
                local_conn.rollback()
                if self.fs:
                    self.fs.write(f"    Error writing to local DB: {e}\n")
                raise
            finally:
                local_conn.close()

            sql_conn.close()
            
            return True

        except Exception as e:
            if self.fs:
                self.fs.write(f"    Sync failed: {e}\n")
            return False

    def create_zip(self) -> str:
        """Creates a zip file of the SQLite database and removes any old zip files."""
        if self.fs:
            self.fs.write(f"[*] Creating zip archive of {self.local_db_path}...\n")
        
        for file in Path(self.zip_folder).glob("*.zip"):
            file.unlink()
            if self.fs:
                self.fs.write(f"    Removed old zip: {file}\n")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"database_backup_{timestamp}.zip"
        zip_path = os.path.join(self.zip_folder, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(self.local_db_path, arcname=os.path.basename(self.local_db_path))
        
        if self.fs:
            self.fs.write(f"    Created zip: {zip_path}\n")
        return zip_path

    def send_email(self, zip_path: str):
        """Sends the zipped database file via email."""
        if not self.email_config:
            if self.fs:
                self.fs.write("    No email configuration provided, skipping email.\n")
            return
        
        if self.fs:
            self.fs.write(f"[*] Sending email to {self.email_config['to_email']}...\n")
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            msg['Subject'] = self.email_config.get('subject', f"Database Backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
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
        
        :param tables_to_sync: List of tuples (table_name, pk_column, timestamp_column) 
                               or (table_name, pk_column, timestamp_column, schema)
        """
        if self.fs:
            self.fs.write("\n" + "="*50 )
            self.fs.write(f"Starting sync at {datetime.now()}")
            self.fs.write("="*50 + "\n")
        
        changes_detected = False
        
        for table_info in tables_to_sync:
            if len(table_info) == 4:
                table, pk, time_col, schema = table_info
            else:
                table, pk, time_col = table_info
                schema = "dbo"  # Default schema
            
            if self.sync_table(table, pk, time_col, schema):
                changes_detected = True
        
        if changes_detected:
            if self.fs:
                self.fs.write("\n[*] Changes detected! Creating backup and sending email...\n")
            zip_path = self.create_zip()
            self.send_email(zip_path)
        else:
            if self.fs:
                self.fs.write("\n[*] No changes detected. Skipping backup.\n")
    def _convert_value_for_sqlite(self, value):
        """
        Convert SQL Server values to SQLite-compatible types.
        Handles decimal.Decimal, datetime, and other unsupported types.
        """
        if value is None:
            return None
        elif isinstance(value, Decimal):
            # Convert Decimal to float for SQLite
            return float(value)
        elif isinstance(value, datetime):
            # Convert datetime to ISO format string
            return value.isoformat()
        elif isinstance(value, bytes):
            # Keep bytes as-is (BLOB)
            return value
        elif isinstance(value, (int, float, str)):
            # These types are natively supported
            return value
        else:
            # Convert any other type to string
            return str(value)

    def _convert_row_for_sqlite(self, row):
        """
        Convert an entire row tuple to SQLite-compatible values.
        """
        return tuple(self._convert_value_for_sqlite(val) for val in row)







class PythonService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WAZAPOS_TEST"              # Service name (unique)
    _svc_display_name_ = "WAZAPOS_TEST"    # Display name in Windows Services
    _svc_description_ = "Runs a Python script in the background as a Windows service"

    

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
        servicemanager.LogInfoMsg("MyPythonService - Starting service...")
        
        
        log_folder = rf"{BASE_FOLDER}\logs"
        os.makedirs(LOCAL_DB_PATH, exist_ok=True)
        os.makedirs(ZIP_FOLDER, exist_ok=True)
        os.makedirs(log_folder, exist_ok=True)

        
        while self.running:
            # 👉 Put your custom Python code here
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
                        'dsn': config_rows[1]
                    }
                    # sql_config = {
                    #     'username': 'superadmin',
                    #     'password': 'MotDePasseFort123!',
                    #     'server': '192.168.2.41,1433',
                    #     'database': 'x3waza',
                    #     'driver': 'ODBC Driver 17 for SQL Server'
                    # }

                    f.write(f"Config: {config_rows}\n")

                    folder_conn = sqlite3.connect(db_path)
                    folder_cursor = folder_conn.cursor()
                    folder_cursor.execute("SELECT * FROM configurations_folders")
                    folder_rows = folder_cursor.fetchone()
                    folder_conn.close()

                    f.write(f"Folder: {folder_rows}\n")


                    email_conn = sqlite3.connect(db_path)
                    email_cursor = email_conn.cursor()
                    email_cursor.execute("SELECT * FROM email_configs")
                    email_rows = email_cursor.fetchone()
                    email_conn.close()
                    
                    f.write(f"Email: {email_rows}\n")

                    email_config = {
                        'smtp_server': email_rows[1],
                        'smtp_port': email_rows[4],
                        'smtp_username': email_rows[2],
                        'smtp_password': email_rows[3],
                        'from_email': email_rows[2],
                        'to_email': email_rows[5],
                        'subject': 'Database Backup Update'
                    }

                    syncer = DatabaseSync(
                        sql_config, 
                        local_db_path=rf"{LOCAL_DB_PATH}\local_data.db",
                        zip_folder=ZIP_FOLDER,
                        email_config=email_config,
                        fs = f
                    )

                    tables_to_sync = [
                        ("ITMMASTER", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("ITMFACILIT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("ITMSALES", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPARTNER", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPCUSTOMER", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPCUSTMVT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPDLVCUST", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SALESREP", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SPRICLINK", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("PRICSTRUCT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SPREASON", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SPRICCONF", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SPRICLIST", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SORDER", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("PIMPL", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABMODELIV", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("STOCK", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("FACILITY", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SORDER", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPCARRIER", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("COMPANY", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPDLVCUST", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABSOHTYP", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABVACBPR", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SVCRVAT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("ITMCATEG", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("CBLOB", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("ABLOB", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("AUTILIS", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("AMENUSER", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABVAT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPADDRESS", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("WAREHOUSE", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABMODELIV", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABPAYTERM", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABDEPAGIO", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("BPCINVVAT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABVAT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABRATVAT", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABVACITM", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TABVAC", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("TAXLINK", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SFOOTINV", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SORDERQ", "AUUID_0", "UPDDATTIM_0", "SEED"),
                        ("SORDERP", "AUUID_0", "UPDDATTIM_0", "SEED"),
                    ]

                                        # Common Sage X3 schemas: "WAZA", "x3", "SEED", etc.
                    # You can find your schema by running: SELECT DISTINCT TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ITMMASTER'
 
                    syncer.run_sync(tables_to_sync)
                    f.write(f"\nSleeping for 60 seconds... (Press Ctrl+C to stop)")
                    time.sleep(60)

   
                    f.write("Service is running...\n")

                except Exception as e:
                    f.write(f"Error in service execution: {e}\n")

            time.sleep(60)  # Wait 60 seconds before next loop

        servicemanager.LogInfoMsg("MyPythonService - Service stopped.")


# Exemple d'utilisation
    
if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)
    

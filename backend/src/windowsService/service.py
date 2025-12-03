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
        local_db_path: str = rf"{LOCAL_DB_PATH}\local_data.db",
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
        self.local_db_path = local_db_path
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
        self._export_tables_db(self.tables_to_sync)

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

    def _get_local_connection(self):
        """Creates a connection to the local SQLite database with performance optimizations."""
        conn = sqlite3.connect(self.local_db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        
        # Set text_factory to handle potential encoding issues
        conn.text_factory = lambda x: x.decode('latin-1', errors='replace') if isinstance(x, bytes) else x
        
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        # Faster writes with NORMAL synchronous mode
        conn.execute("PRAGMA synchronous=NORMAL")
        # Increase cache size for better performance
        conn.execute("PRAGMA cache_size=10000")
        # Faster writes with IMMEDIATE transactions
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.commit()
        
        return conn

    def _init_local_db(self):
        """Creates necessary metadata tables in local DB if they don't exist."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_state (
                    table_name TEXT PRIMARY KEY,
                    last_sync_timestamp DATETIME,
                    is_first_sync INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT,
                    pk_value TEXT,
                    change_type TEXT,
                    sync_timestamp DATETIME
                )
            """)
            conn.commit()

    def _init_first_launch(self):

        if self.fs:
            self.fs.write("[*] Initializing first launch flag in local DB...\n")
        
        with self._get_local_connection() as conn:
            cursor = conn.cursor()

    def _export_tables_db(self, tables: List[str]):
        sqlite_path = self.local_db_path
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cur = sqlite_conn.cursor()

        with self._get_local_connection() as conn:
            sql_cursor = conn.cursor()

            for table in tables:
                if self.fs:
                    self.fs.write(f"[*] Exporting table {table} to local DB...\n")
                
                full_table = f"{self.email_config['schema']}.{table}" # type: ignore

                # Fetch column definitions from SQL Server
                sql_cursor.execute(f'SELECT * FROM "{full_table}"')
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

            sqlite_conn.commit()

            if self.fs:
                self.fs.write(f"[*] Export completed. Local DB path: {sqlite_path}\n")
        
        if self.fs:
            self.fs.write(f"[*] Exported tables to local DB at {sqlite_path}\n")
        
        sqlite_conn.close()
        conn.close()


    def get_last_sync_time(self, table_name: str) -> datetime:
        """Retrieves the last successful sync timestamp for a table."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_sync_timestamp FROM sync_state WHERE table_name = ?", (table_name,))
            row = cursor.fetchone()
            
            if row and row['last_sync_timestamp']:
                return datetime.fromisoformat(row['last_sync_timestamp'])
            
            return datetime.min

    def is_first_sync(self, table_name: str) -> bool:
        """Check if this is the first sync for the table."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_first_sync FROM sync_state WHERE table_name = ?", (table_name,))
            row = cursor.fetchone()
            
            if row:
                return bool(row['is_first_sync'])
            return True  # Default to first sync if no record exists

    def update_sync_time(self, table_name: str, sync_time: datetime, is_first_sync: bool = False):
        """Updates the last sync timestamp and first_sync status."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sync_state (table_name, last_sync_timestamp, is_first_sync)
                VALUES (?, ?, ?)
            """, (table_name, sync_time.isoformat(), 0))  # Always set to 0 after sync
            conn.commit()

    def track_changes(self, table_name: str, pk_value: str, change_type: str):
        """Track which rows were changed for delta export."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_changes (table_name, pk_value, change_type, sync_timestamp)
                VALUES (?, ?, ?, ?)
            """, (table_name, pk_value, change_type, datetime.now().isoformat()))
            conn.commit()

    def clear_change_tracking(self):
        """Clear all tracked changes after successful email send."""
        with self._get_local_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_changes")
            conn.commit()
            if self.fs:
                self.fs.write("    Cleared change tracking table.\n")

    def ensure_local_table_exists(self, table_name: str, columns: List[tuple], pk_column: str):
        """
        Creates the local table if it doesn't exist, matching the source schema.
        
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
        
        ALWAYS does UPSERT (INSERT OR REPLACE) - never recreates the table
        First sync loads all rows, subsequent syncs only load changed rows
        Uses BATCH INSERTS for 10-100x performance improvement
        
        :param table_name: Name of the table to sync
        :param pk_column: Primary key column name (for upserts)
        :param timestamp_column: Column used to track changes (e.g., UpdatedAt, ModifiedDate)
        :param schema: Schema name (default: dbo)
        :return: True if changes were made, False otherwise
        """
        if self.fs:
            self.fs.write(f"[*] Starting sync for table: {schema}.{table_name}\n")
        
        first_sync = self.is_first_sync(table_name)
        last_sync = self.get_last_sync_time(table_name)
        
        if first_sync:
            if self.fs:
                self.fs.write(f"    FIRST LOAD - Fetching ALL rows from {schema}.{table_name}\n")
        else:
            if self.fs:
                self.fs.write(f"    Delta sync. Last sync time: {last_sync}\n")

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
                    self.fs.write(f"    Warning: No columns found for {schema}.{table_name}, trying without schema filter...\n")
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
            
            if first_sync:
                query = f'SELECT {cols_str} FROM "{schema}"."{table_name}"'
                if self.fs:
                    self.fs.write(f"    Executing FULL LOAD query...\n")
                sql_cursor.execute(query)
            else:
                query = f'SELECT {cols_str} FROM "{schema}"."{table_name}" WHERE "{timestamp_column}" > ?'
                if self.fs:
                    self.fs.write(f"    Executing DELTA query...\n")
                sql_cursor.execute(query, last_sync)
            
            rows = sql_cursor.fetchall()
            
            if not rows:
                if self.fs:
                    self.fs.write("    No new changes found.\n")
                sql_conn.close()
                return False

            if self.fs:
                self.fs.write(f"    Found {len(rows)} records to {'LOAD' if first_sync else 'UPDATE'}.\n")

            converted_rows = []
            pk_tracking = []
            new_max_date = last_sync
            skipped_rows = 0
            
            for row in rows:
                try:
                    values = self._convert_row_for_sqlite(tuple(row))
                    converted_rows.append(values)
                    
                    # Track primary keys and find max timestamp
                    try:
                        pk_index = unique_col_names.index(pk_column)
                        pk_value = str(values[pk_index])
                        pk_tracking.append((table_name, pk_value, "UPSERT"))
                    except (ValueError, IndexError):
                        pass
                    
                    try:
                        ts_index = unique_col_names.index(timestamp_column)
                        row_date = values[ts_index]
                        
                        if row_date:
                            if isinstance(row_date, str):
                                try:
                                    row_date = datetime.fromisoformat(row_date)
                                except ValueError:
                                    pass
                            
                            if isinstance(row_date, datetime) and row_date > new_max_date:
                                new_max_date = row_date
                    except (ValueError, IndexError):
                        pass
                
                except (UnicodeDecodeError, UnicodeEncodeError) as e:
                    skipped_rows += 1
                    if self.fs:
                        self.fs.write(f"    Warning: Encoding error in row, skipping: {e}\n")
                    continue

            if skipped_rows > 0 and self.fs:
                self.fs.write(f"    Skipped {skipped_rows} rows due to encoding errors.\n")

            local_conn = self._get_local_connection()
            local_cursor = local_conn.cursor()
            
            try:
                local_cursor.execute("BEGIN TRANSACTION")
                
                # ALWAYS UPSERT - never recreate table
                upsert_sql = f"""
                    INSERT OR REPLACE INTO "{table_name}" ({cols_str})
                    VALUES ({placeholders})
                """
                local_cursor.executemany(upsert_sql, converted_rows)
                
                # Batch insert all change tracking records
                if pk_tracking:
                    local_cursor.executemany(
                        "INSERT INTO sync_changes (table_name, pk_value, change_type, sync_timestamp) VALUES (?, ?, ?, ?)",
                        [(t[0], t[1], t[2], datetime.now().isoformat()) for t in pk_tracking]
                    )
                
                local_conn.commit()
                
                self.update_sync_time(table_name, new_max_date, is_first_sync=False)
                if self.fs:
                    sync_type = "FIRST LOAD (UPSERT)" if first_sync else "Delta sync (UPSERT)"
                    self.fs.write(f"    Successfully synced ({sync_type}). New watermark: {new_max_date}\n")
                
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

    def export_delta_data_with_full_rows(self) -> Optional[str]:
        """
        Export only the CHANGED ROWS (full row data) to a CSV file.
        This retrieves the actual row data from local DB based on tracked changes.
        """
        try:
            with self._get_local_connection() as conn:
                cursor = conn.cursor()
                
                # Get all tracked changes
                cursor.execute("""
                    SELECT DISTINCT table_name, pk_value
                    FROM sync_changes
                    ORDER BY table_name
                """)
                changes = cursor.fetchall()
                
                if not changes:
                    if self.fs:
                        self.fs.write("    No changes to export.\n")
                    return None
                
                # Group changes by table
                table_changes = {}
                for change in changes:
                    table = change['table_name']
                    pk = change['pk_value']
                    if table not in table_changes:
                        table_changes[table] = []
                    table_changes[table].append(pk)
                
                # Create CSV file with FULL ROW DATA
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                delta_file = os.path.join(DELTA_FOLDER, f"delta_records_{timestamp}.csv")
                
                with open(delta_file, 'w', encoding='utf-8', newline='') as f:
                    writer = None
                    current_table = None
                    
                    for table_name, pk_values in table_changes.items():
                        # Get column names for this table
                        cursor.execute(f'PRAGMA table_info("{table_name}")')
                        columns_info = cursor.fetchall()
                        column_names = [col[1] for col in columns_info]  # col[1] is the column name
                        pk_column = column_names[0]  # Default to first column
                        
                        # Find actual PK column
                        for col in columns_info:
                            if col[5] == 1:  # col[5] is pk flag
                                pk_column = col[1]
                                break
                        
                        # Fetch actual rows for these primary keys
                        placeholders = ','.join(['?' for _ in pk_values])
                        query = f'SELECT * FROM "{table_name}" WHERE "{pk_column}" IN ({placeholders})'
                        cursor.execute(query, pk_values)
                        rows = cursor.fetchall()
                        
                        if not rows:
                            continue
                        
                        # Write table header and data
                        if current_table != table_name:
                            if current_table is not None:
                                f.write('\n')  # Separator between tables
                            f.write(f"TABLE: {table_name}\n")
                            # Write column headers
                            f.write(','.join(column_names) + '\n')
                            current_table = table_name
                        
                        # Write actual row data
                        for row in rows:
                            row_data = [str(val) if val is not None else '' for val in row]
                            f.write(','.join(row_data) + '\n')
                
                if self.fs:
                    self.fs.write(f"    Delta records (full rows) exported to: {delta_file}\n")
                    self.fs.write(f"    Total tables with changes: {len(table_changes)}\n")
                
                return delta_file
        except Exception as e:
            if self.fs:
                self.fs.write(f"    Error exporting delta data: {e}\n")
            return None

    def create_zip(self, is_first_sync: bool) -> Optional[str]:
        """
        Creates a zip file:
        - First sync: Full database (local_data.db)
        - Delta sync: Only changed records (CSV with full row data)
        
        :param is_first_sync: Whether this is a first-time full load
        """
        if self.fs:
            sync_type = "FIRST LOAD" if is_first_sync else "DELTA"
            self.fs.write(f"[*] Creating {sync_type} zip archive...\n")
        
        # Remove old zip files
        for file in Path(self.zip_folder).glob("*.zip"):
            file.unlink()
            if self.fs:
                self.fs.write(f"    Removed old zip: {file}\n")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if is_first_sync:
            zip_filename = f"database_full_{timestamp}.zip"
            zip_path = os.path.join(self.zip_folder, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(self.local_db_path, arcname=os.path.basename(self.local_db_path))
            
            if self.fs:
                self.fs.write(f"    Created FULL database zip: {zip_path}\n")
        else:
            # Export FULL ROW DATA for changed records only
            delta_file = self.export_delta_data_with_full_rows()
            if not delta_file:
                if self.fs:
                    self.fs.write("    No delta file to zip.\n")
                return None
            
            zip_filename = f"database_delta_{timestamp}.zip"
            zip_path = os.path.join(self.zip_folder, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(delta_file, arcname=os.path.basename(delta_file))
            
            if self.fs:
                self.fs.write(f"    Created DELTA zip with full row data: {zip_path}\n")

        return zip_path

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
            self.fs.write("\n" + "="*50 + "\n")
            self.fs.write(f"Starting sync at {datetime.now()}\n")
            self.fs.write("="*50 + "\n")
        
        changes_detected = False
        first_sync_with_data = False
        
        for table_info in tables_to_sync:
            if len(table_info) == 4:
                table, pk, time_col, schema = table_info
            else:
                table, pk, time_col = table_info
                schema = "dbo"
            
            was_first_sync = self.is_first_sync(table)
            had_changes = self.sync_table(table, pk, time_col, schema)
            
            # Only consider it "first sync" if the table actually had data
            if was_first_sync and had_changes:
                first_sync_with_data = True
            
            if had_changes:
                changes_detected = True
        
        if changes_detected:
            if self.fs:
                sync_label = "FIRST LOAD" if first_sync_with_data else "DELTA"
                self.fs.write(f"\n[*] Changes detected! Creating {sync_label} backup and sending email...\n")
            
            zip_path = self.create_zip(is_first_sync=first_sync_with_data)
            if zip_path:
                self.send_email(zip_path, is_first_sync=first_sync_with_data)
                # Only clear tracking after DELTA sync, not after first load
                if not first_sync_with_data:
                    self.clear_change_tracking()
        else:
            if self.fs:
                self.fs.write("\n[*] No changes detected. Skipping backup.\n")

    def _convert_value_for_sqlite(self, value):
        """
        Convert SQL Server values to SQLite-compatible types.
        Handles decimal.Decimal, datetime, and other unsupported types.
        Includes robust encoding handling for text data.
        """
        if value is None:
            return None
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, bytes):
            # Try multiple encodings for byte data
            try:
                return value.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return value.decode('latin-1')
                except UnicodeDecodeError:
                    try:
                        return value.decode('cp1252', errors='replace')
                    except:
                        return value.decode('ascii', errors='replace')
        elif isinstance(value, str):
            # Ensure string is properly encoded
            return value
        elif isinstance(value, (int, float)):
            return value
        else:
            return str(value)

    def _convert_row_for_sqlite(self, row):
        """
        Convert an entire row tuple to SQLite-compatible values.
        """
        return tuple(self._convert_value_for_sqlite(val) for val in row)

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
                        "FACILITY",
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
        
                syncer = DatabaseSync(
                            sql_config,
                            tables_to_sync=tables_to_sync,
                            local_db_path=rf"{LOCAL_DB_PATH}\local_data.db",
                            zip_folder=ZIP_FOLDER,
                            email_config=email_config,
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

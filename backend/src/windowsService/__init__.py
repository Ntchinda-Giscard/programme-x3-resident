import pyodbc
import sqlite3
import time
import zipfile
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from decimal import Decimal
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.FileHandler('fastapi.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseSync:
    def __init__(
        self, 
        sql_server_config: Dict[str, str], 
        local_db_path: str = "local_data.db",
        zip_folder: str = "database_backup",
        email_config: Optional[Dict[str, str]] = None
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
        
        # Create zip folder if it doesn't exist
        Path(self.zip_folder).mkdir(parents=True, exist_ok=True)
        
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
        
        logger.info(f"[*] Connecting with: {conn_str.replace(password or '', '***') if password else conn_str}")
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
        logger.info(f"[*] Starting sync for table: {schema}.{table_name}")
        
        last_sync = self.get_last_sync_time(table_name)
        logger.info(f"    Last sync time: {last_sync}")

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
                logger.info(f"    Warning: No columns found for {schema}.{table_name}, trying without schema filter...")
                sql_cursor.execute(f"""
                    SELECT DISTINCT COLUMN_NAME, DATA_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = ?
                    ORDER BY COLUMN_NAME
                """, (table_name,))
                columns = [(row.COLUMN_NAME, row.DATA_TYPE) for row in sql_cursor.fetchall()]
                
                if not columns:
                    logger.info(f"    Error: Table {table_name} not found in SQL Server.")
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
                logger.info("    No new changes found.")
                sql_conn.close()
                return False

            logger.info(f"    Found {len(rows)} records to update.")

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
                logger.info(f"    Successfully synced. New watermark: {new_max_date}")
                
            except Exception as e:
                local_conn.rollback()
                logger.info(f"    Error writing to local DB: {e}")
                raise
            finally:
                local_conn.close()

            sql_conn.close()
            
            return True

        except Exception as e:
            logger.info(f"    Sync failed: {e}")
            return False

    def create_zip(self) -> str:
        """Creates a zip file of the SQLite database and removes any old zip files."""
        logger.info(f"[*] Creating zip archive of {self.local_db_path}...")
        
        for file in Path(self.zip_folder).glob("*.zip"):
            file.unlink()
            logger.info(f"    Removed old zip: {file}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"database_backup_{timestamp}.zip"
        zip_path = os.path.join(self.zip_folder, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(self.local_db_path, arcname=os.path.basename(self.local_db_path))
        
        logger.info(f"    Created zip: {zip_path}")
        return zip_path

    def send_email(self, zip_path: str):
        """Sends the zipped database file via email."""
        if not self.email_config:
            logger.info("    No email configuration provided, skipping email.")
            return
        
        logger.info(f"[*] Sending email to {self.email_config['to_email']}...")
        
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
            
            logger.info(f"    Email sent successfully!")
            
        except Exception as e:
            logger.error(f"    Error sending email: {e}")

    def run_sync(self, tables_to_sync: List[tuple]):
        """
        Runs the sync process for all specified tables.
        
        :param tables_to_sync: List of tuples (table_name, pk_column, timestamp_column) 
                               or (table_name, pk_column, timestamp_column, schema)
        """
        logger.info("\n" + "="*50)
        logger.info(f"Starting sync at {datetime.now()}")
        logger.info("="*50)
        
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
            logger.info("\n[*] Changes detected! Creating backup and sending email...")
            zip_path = self.create_zip()
            self.send_email(zip_path)
        else:
            logger.info("\n[*] No changes detected. Skipping backup.")

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


# Example Usage
if __name__ == "__main__":
    sql_config = {
        'username': 'superadmin',
        'password': 'MotDePasseFort123!',
        'server': '192.168.2.41,1433',
        'database': 'x3waza',
        'driver': 'ODBC Driver 17 for SQL Server'
    }
    
    email_config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 465,
        'smtp_username': 'ntchinda1998@gmail.com',
        'smtp_password': 'txdp zcoh ucum ezxt',
        'from_email': 'ntchinda1998@gmail.com',
        'to_email': 'giscardntchinda@gmail.com',
        'subject': 'Database Backup Update'
    }

    syncer = DatabaseSync(
        sql_config, 
        local_db_path="local_data.db",
        zip_folder=r"C:\temp",
        email_config=email_config
    )

    # Common Sage X3 schemas: "WAZA", "x3", "SEED", etc.
    # You can find your schema by running: SELECT DISTINCT TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ITMMASTER'
    tables_to_sync = [
        ("ITMMASTER", "AUUID_0", "UPDDATTIM_0", "SEED"),
        ("ITMFACILIT", "AUUID_0", "UPDDATTIM_0", "SEED"),
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
    ]

    logger.info("Starting Database Sync Service...")
    
    try:
        while True:
            syncer.run_sync(tables_to_sync)
            logger.info(f"\nSleeping for 60 seconds... (Press Ctrl+C to stop)")
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.error("\nSync service stopped.")

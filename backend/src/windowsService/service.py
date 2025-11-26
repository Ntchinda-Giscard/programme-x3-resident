# import boto3
# from botocore.exceptions import ClientError
from typing import Dict, List, Optional
import win32serviceutil
import win32service
import win32event
import servicemanager
import time
from datetime import datetime
import pyodbc
import sqlite3
from decimal import Decimal
import logging
from email.message import EmailMessage
import smtplib
import ssl
import mimetypes
from pathlib import Path
import zipfile
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def connect_to_database(dsn, database, username=None, password=None):
    """
    Connects to a SQL Server database using either Windows Authentication or SQL Server Authentication.

    Parameters:
    - dsn (str): The Data Source Name configured in ODBC.
    - username (str, optional): The SQL Server username (required for SQL Server Authentication).
    - password (str, optional): The SQL Server password (required for SQL Server Authentication).
    - database (str, optional): The name of the specific database to connect to.

    Returns:
    - pyodbc.Connection: A connection object to the database.
    """
    try:
        connection_str = f'DSN={dsn};'
        if database:
            connection_str += f'DATABASE={database};'

        if username and password:
            connection_str += f'UID={username};PWD={password};'
        else:
            connection_str += 'Trusted_Connection=yes;'
        
        conn = pyodbc.connect(connection_str)
    
        return conn

    except pyodbc.Error as e:
        raise Exception(f"Failed to connect to database: {str(e)}")  


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s - %(lineno)d - %(threadName)s',
    handlers=[
        logging.FileHandler('fastapi.log')
    ]
)
logger = logging.getLogger(__name__)

# txdp zcoh ucum ezxt
# ntchinda1998@gmail.com

def send_email(
    email_receiver: str,
    server: str,
    port: int,
    email_sender: str,
    email_password: str,
    security: str = "tls",  # "ssl", "tls" ou "both"
    attachments: Optional[list[str]] = None,
    subject: Optional[str] = None,
    message: Optional[str] = None
):
    # Vérification du paramètre security
    mode = security.lower()
    if mode not in ("ssl", "tls", "both"):
        raise ValueError(f"Paramètre 'security' invalide : {security}. Attendu : 'ssl', 'tls' ou 'both'.")

    subject = subject or "Votre bulletin de paie"
    # The issue is in this body text - there are invisible non-breaking spaces (\xa0)
    # Let's clean them up while preserving the text content
    body = message or "Veuillez trouver en piece jointe votre bulletin de paie pour le mois"

    # Création du message with explicit UTF-8 encoding
    em = EmailMessage()
    em["From"] = email_sender
    em["To"] = email_receiver
    em["Subject"] = subject
    em.set_content(body, charset='utf-8')

    # Ajout des pièces jointes
    for file_path in attachments or []:
        path = Path(file_path)
        if not path.is_file():
            logger.info(f"Fichier introuvable : {file_path}")
            continue
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "application/octet-stream"
        maintype, subtype = mime_type.split("/", 1)
        with open(path, "rb") as f:
            em.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=path.name)

    context = ssl.create_default_context()

    # Fonctions internes pour tenter une connexion
    def try_ssl():
        with smtplib.SMTP_SSL(server, port, context=context) as smtp:
            smtp.login(email_sender, email_password)
            logger.info(f"Connexion réussie à {server}:{port} avec SSL.")
            smtp.send_message(em)

    def try_tls():
        with smtplib.SMTP(server, port) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(email_sender, email_password)
            logger.info(f"Connexion réussie à {server}:{port} avec STARTTLS.")
            smtp.send_message(em)

    # Gestion des différentes options
    try:
        if mode == "ssl":
            logger.info(f"Tentative SSL sur {server}:{port}")
            try_ssl()
            logger.info("Email envoyé avec SSL.")
        elif mode == "tls":
            logger.info(f"Tentative STARTTLS sur {server}:{port}")
            try_tls()
            logger.info("Email envoyé avec STARTTLS.")
        elif mode == "both":
            # Essai SSL puis TLS si échec
            try:
                logger.info(f"[BOTH] Tentative SSL sur {server}:{port}")
                try_ssl()
                logger.info("Email envoyé avec SSL.")
            except Exception as e_ssl:
                logger.info(f"Échec SSL : {e_ssl}")
                try:
                    logger.info(f"[BOTH] Tentative STARTTLS sur {server}:{port}")
                    try_tls()
                    logger.info("Email envoyé avec STARTTLS.")
                except Exception as e_tls:
                    raise RuntimeError(
                        f"Échec des deux méthodes sur {server}:{port}.\n"
                        f"- SSL error: {e_ssl}\n"
                        f"- STARTTLS error: {e_tls}"
                    ) from e_tls
    except Exception as e:
        # Handle Unicode characters in error messages properly
        try:
            error_msg = str(e)
            logger.error(f"Échec de l'envoi : {error_msg}")
        except UnicodeEncodeError:
            # If the error message contains problematic characters, handle them
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            logger.error(f"Échec de l'envoi : {error_msg}")
        except Exception as log_error:
            # Last resort: use the original method to clean the error
            logger.error(f"Erreur de logging : {log_error}")
        raise e

LOCAL_DB_PATH = r"C:\poswaza\temp\db"
ZIP_FOLDER = r"C:\poswaza\temp\zip"

class DatabaseSync:
    def __init__(
        self, 
        sql_server_config: Dict[str, str], 
        local_db_path: str = rf"{LOCAL_DB_PATH}\local_data.db",
        zip_folder: str = ZIP_FOLDER,
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
        
        

        

        while self.running:
            # 👉 Put your custom Python code here
            with open("C:\\service_log.txt", "a") as f:
                try:
                    db_path = r"c:/posdatabase/config.db"

                    config_conn = sqlite3.connect(db_path)
                    config_cursor = config_conn.cursor()
                    config_cursor.execute("SELECT * FROM database_configuration")
                    config_rows = config_cursor.fetchone()
                    config_conn.close()

                    folder_conn = sqlite3.connect(db_path)
                    folder_cursor = folder_conn.cursor()
                    folder_cursor.execute("SELECT * FROM configurations_folders")
                    folder_rows = folder_cursor.fetchone()
                    folder_conn.close()


                    email_conn = sqlite3.connect(db_path)
                    email_cursor = email_conn.cursor()
                    email_cursor.execute("SELECT * FROM email_configs")
                    email_rows = email_cursor.fetchone()
                    email_conn.close()

                    sqlserver_conn = pyodbc.connect(
                        "DRIVER={ODBC Driver 17 for SQL Server};"
                        "SERVER=192.168.2.41,1433;"
                        "DATABASE=x3waza;"
                        "UID=superadmin;"
                        "PWD=MotDePasseFort123!;"
                    )

                    # sqlserver_conn = connect_to_database(
                    #     dsn= config_rows[1], database="x3waza", username=config_rows[6], password=config_rows[7])

                    db_path_sqlite = f"{folder_rows[1]}/{datetime.now().strftime('%Y%m%d%H%M%S')}_sagex3_seed.db"
                    sqlserver_cursor = sqlserver_conn.cursor()
                    sqlite_conn = sqlite3.connect(db_path_sqlite, timeout=30, check_same_thread=False)
                    sqlite_cursor = sqlite_conn.cursor()
                    
                    
                    tables = [
        "ITMMASTER",
        "ITMSALES",
        "ITMFACILIT",
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
        "SORDER",
        "BPCARRIER",
        "COMPANY",
        "BPDLVCUST",
        "TABSOHTYP",
        "TABVACBPR",
        "SVCRVAT",
        "ITMCATEG",
        "CBLOB",
        "BLOBEXPENSES",
        "ABLOB",
        "AUTILIS",
        "AMENUSER",
        "TABVAT",
        "BPADDRESS",
        "WAREHOUSE",
        "TABMODELIV",
        "TABPAYTERM",
        "TABDEPAGIO",
        "BPCINVVAT",
        "TABVAT",
        "TABRATVAT",
        "TABVACITM",
        "TABVAC",
        "TAXLINK",
        "SFOOTINV",
        "SORDERQ",
        "SORDERP"
    ]

                    for table in tables:
                        # print(f" Processing table: SEED.{table}")

                        # --- Get column names ---
                        sqlserver_cursor.execute(f"SELECT TOP 0 * FROM SEED.{table}")
                        columns = [col[0] for col in sqlserver_cursor.description]

                        # --- Drop + create SQLite table ---
                        col_defs = ", ".join([f'"{c}" TEXT' for c in columns])
                        sqlite_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                        sqlite_cursor.execute(f"CREATE TABLE {table} ({col_defs})")

                        # --- Fetch all rows from SQL Server ---
                        sqlserver_cursor.execute(f"SELECT * FROM SEED.{table}")
                        rows = sqlserver_cursor.fetchall()

                        # --- Convert Decimal to float/str for SQLite ---
                        def convert_row(row):
                            return [float(x) if isinstance(x, Decimal) else x for x in row]

                        converted_rows = [convert_row(r) for r in rows]

                        # --- Insert into SQLite ---
                        placeholders = ", ".join(["?"] * len(columns))
                        insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"
                        sqlite_cursor.executemany(insert_sql, converted_rows)
                        sqlite_conn.commit()

                        # print(f" {table}: {len(rows)} rows copied.")

                    # --- Close connections ---
                    sqlserver_conn.close()
                    sqlite_conn.close()

                    zip_path = db_path_sqlite.replace('.db', '.zip')
                    try:
                        # First, remove any old zip files in the directory
                        zip_dir = os.path.dirname(zip_path)
                        for old_file in os.listdir(zip_dir):
                            if old_file.endswith('_sagex3_seed.zip'):
                                old_zip_path = os.path.join(zip_dir, old_file)
                                try:
                                    os.remove(old_zip_path)
                                except OSError:
                                    pass
                        
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            zipf.write(db_path_sqlite, os.path.basename(db_path_sqlite))
                        
                        file_to_send = zip_path
                        f.write(f"Compressed successfully. Size: {os.path.getsize(zip_path)} bytes.\n")
                        
                        # Remove original large file immediately after compression
                        try:
                            os.remove(db_path_sqlite)
                        except OSError:
                            pass
                            
                    except Exception as e:
                        f.write(f"Error compressing file: {e}\n")
                        # Fallback to original file if compression fails
                        file_to_send = db_path_sqlite

                    security = "ssl"
                    if email_rows[6] is True:
                        security = "ssl"
                    elif email_rows[5] is True:
                        security = "tls"
                    elif email_rows[5] is True and email_rows[6] is True:
                        security = "both"

                    attachments_list = [file_to_send] if file_to_send else []

                    if attachments_list:
                        send_email(
                            email_receiver="giscardntchinda@gmail.com",
                            server=email_rows[1],
                            port=email_rows[4],  # Port fourni par l'utilisateur
                            email_sender=email_rows[2],
                            email_password=email_rows[3],
                            security=security,  # "ssl", "tls", "both" # type: ignore
                            attachments=attachments_list
                        )
                        f.write(f"Email sent successfully with attachment: {file_to_send}\n")
                    else:
                        f.write("Skipping email sending because attachment was too large or invalid.\n")
                    
                    # Only clean up the original .db file if it still exists
                    if os.path.exists(db_path_sqlite):
                        try:
                            os.remove(db_path_sqlite)
                        except OSError:
                            pass

                    f.write(f"Connected to obdc.\n {config_rows} dsn= {config_rows[1]}, username={config_rows[6]}, password={config_rows[7]}, database=x3waza ")
                    f.write(f"Email config: {email_rows}\n")
                except Exception as e:
                    f.write(f"Error connecting to SQL Server: {e}\n")

            time.sleep(60)  # Wait 60 seconds before next loop

        servicemanager.LogInfoMsg("MyPythonService - Service stopped.")

    # def SvcDoRun(self):
    #     """Main entry point for service logic"""
    #     log_message("Service started successfully.")
    #     self.main_loop()
    
    # def main_loop(self):
    #     """Main loop that runs periodically"""
    #     while self.running:
    #         log_message("Heartbeat: Service is running.")
    #         time.sleep(300)  # Log every 5 minutes

        # log_message("Service stopped.")

# Exemple d'utilisation
    
if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)
    send_email(
        email_receiver="destinataire@exemple.com",
        server="smtp.exemple.com",
        port=587,  # Port fourni par l'utilisateur
        email_sender="utilisateur@exemple.com",
        email_password="votre_mdp",
        security="both",  # "ssl", "tls", "both"
        attachments=[
            r"C:\chemin\fichier.pdf"
        ]
    )

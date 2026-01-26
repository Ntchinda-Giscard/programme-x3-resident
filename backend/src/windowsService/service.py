import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
import logging
import sqlite3
import pyodbc 
import csv
import smtplib
from pathlib import Path
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional, Tuple

# Setup Logging
BASE_FOLDER = r"C:\poswaza\temp"
LOG_FOLDER = os.path.join(BASE_FOLDER, "logs")
os.makedirs(LOG_FOLDER, exist_ok=True)

log_file_path = os.path.join(LOG_FOLDER, "service.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WazaService")

# Constants
LOCAL_DB_PATH = os.path.join(BASE_FOLDER, "db")
ZIP_FOLDER = os.path.join(BASE_FOLDER, "zip")
DELTA_FOLDER = os.path.join(BASE_FOLDER, "delta")
CONFIG_DB_PATH = os.path.join(LOCAL_DB_PATH, "config.db")

class ConfigLoader:
    """Handles loading configuration from the local SQLite database."""
    
    @staticmethod
    def get_sql_config() -> Dict[str, str]:
        try:
            with sqlite3.connect(CONFIG_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM database_configuration")
                row = cursor.fetchone()
                
                if not row:
                    logger.error("No database configuration found.")
                    return {}
                
                # Assuming row structure matches: id, odbc_source, connection_type, host, port, database, schemas, username, password
                # Adjust indices if model changes. Based on original code:
                # row[1]=dsn, row[3]=host, row[4]=port, row[5]=database, row[6]=schema, row[7]=user, row[8]=pass
                
                return {
                    'username': row[7],
                    'password': row[8],
                    'server': f"{row[3]},{row[4]}",
                    'database': row[5],
                    'driver': 'ODBC Driver 17 for SQL Server',
                    'dsn': row[1],
                    'schema': row[6]
                }
        except Exception as e:
            logger.error(f"Error loading SQL config: {e}")
            return {}

    @staticmethod
    def get_email_config() -> Dict[str, Any]:
        try:
            with sqlite3.connect(CONFIG_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM email_configs")
                row = cursor.fetchone()
                
                if not row:
                    return {}

                # stored in email_configs table
                return {
                    'smtp_server': row[1],
                    'smtp_username': row[2],
                    'smtp_password': row[3],
                    'smtp_port': row[4],
                    'from_email': row[2],
                    'to_email': row[5], # Default receiver if needed
                }
        except Exception as e:
            logger.error(f"Error loading Email config: {e}")
            return {}

    @staticmethod
    def get_site_emails() -> Dict[str, str]:
        try:
            with sqlite3.connect(CONFIG_DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM site_configs")
                rows = cursor.fetchall()
                # row[1] = site, row[2] = email
                return {row[1]: row[2] for row in rows}
        except Exception as e:
            logger.error(f"Error loading site configs: {e}")
            return {}


class EmailSender:
    """Handles email operations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def send_email(self, to_email: str, subject: str, body: str, attachment_path: Optional[str] = None):
        if not self.config:
            logger.warning("Email configuration missing. Skipping email.")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.get('from_email')
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                    msg.attach(part)
            
            smtp_server = self.config.get('smtp_server')
            smtp_port = int(self.config.get('smtp_port', 587))
            
            logger.info(f"Sending email to {to_email} via {smtp_server}:{smtp_port}")
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if self.config.get('smtp_username') and self.config.get('smtp_password'):
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
                server.send_message(msg)
                
            logger.info(f"Email sent successfully to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")

class DatabaseSync:

    def _send_email_report(self, site, email, changes, csv_path):
        total_records = sum(len(rows) for _, (_, rows) in changes.items())
        subject = f"Database Sync - {site} - {len(changes)} tables, {total_records} records"
        
        body = f"Sync Report for {site}\n\n"
        for table, (_, rows) in changes.items():
            body += f"{table}: {len(rows)} records\n"
            
        self.email_sender.send_email(email, subject, body, csv_path)

    def __init__(
        self,
        sql_server_config,
        tables_to_sync,
        local_db_path,
        zip_folder,
        email_config,
        parameters,
        fs=None
    ):
        """
        Initialize the sync manager.
        """
        self.sql_config = sql_server_config
        self.parameters = parameters
        self.zip_folder = zip_folder
        self.email_config = email_config
        self.fs = fs
        self.tables_to_sync = tables_to_sync
        self.local_db_path = local_db_path
        
        # Create folders if they don't exist
        Path(self.zip_folder).mkdir(parents=True, exist_ok=True)
        Path(DELTA_FOLDER).mkdir(parents=True, exist_ok=True)
        os.makedirs(self.local_db_path, exist_ok=True)
        
        # Initialize first launch
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
                    try:
                        # Determine full table name based on site dependency
                        full_table = f"{self.sql_config['schema']}.{table}" # type: ignore

                        if self.fs:
                            self.fs.write(f"[*] Processing table: {table} ({full_table})\n")

                        # First, check if table has tracking columns
                        try:
                            check_columns_query = f"SELECT TOP 1 * FROM {full_table}"
                            sql_cursor.execute(check_columns_query)
                        except Exception as e:
                            if self.fs:
                                self.fs.write(f"    [!] TABLE NOT FOUND or error accessing {full_table}: {e}\n")
                            continue

                        columns = [column[0] for column in sql_cursor.description]
                        has_tracking = 'ZTRANSFERT_0' in columns and 'ZTRANSDATE_0' in columns

                        if self.fs:
                            self.fs.write(f"    Columns found: {len(columns)}, has_tracking: {has_tracking}\n")

                        # Determine the primary key column
                        if table in self.parameters["site_dependent_tables"]: # type: ignore
                            pk_column = self.parameters['site_keys_column'][table] # type: ignore
                        else:
                            pk_column = self.parameters["primary_key_column"] # type: ignore

                        # **STEP 1: UPDATE SQL SERVER FIRST (if has tracking columns)**
                        if has_tracking and pk_column in columns:
                            if self.fs:
                                self.fs.write(f"    Updating tracking columns in SQL Server for {table}...\n")
                            
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
                                    self.fs.write(f"    Updated {total_updated} rows in SQL Server.\n")

                        # **STEP 2: NOW FETCH THE UPDATED DATA**
                        if table in self.parameters["site_dependent_tables"]: # type: ignore
                            query = f"SELECT * FROM {full_table} WHERE {self.parameters['site_keys_column'][table]} = ?" # type: ignore
                            sql_cursor.execute(query, (site,))
                        else:
                            query = f"SELECT * FROM {full_table}"
                            sql_cursor.execute(query)
                        
                        # Create table in SQLite
                        columns_def = ", ".join([f'"{col}" TEXT' for col in columns])
                        sqlite_cur.execute(f"DROP TABLE IF EXISTS {table}")
                        sqlite_cur.execute(f"CREATE TABLE {table} ({columns_def})")

                        # Fetch all data
                        if self.fs:
                            self.fs.write(f"    Fetching data for {table}...\n")
                        rows = sql_cursor.fetchall()
                        
                        if len(rows) > 0:
                            if self.fs:
                                self.fs.write(f"    Found {len(rows)} records. Syncing to SQLite...\n")
                            placeholders = ", ".join(["?"] * len(columns))
                            insert_query = f"INSERT INTO {table} VALUES ({placeholders})"

                            count = 0
                            for row in rows:
                                sqlite_cur.execute(insert_query, tuple(str(x) if x is not None else None for x in row))
                                count += 1
                                if count % 1000 == 0 and self.fs:
                                    self.fs.write(f"    Progress: {count}/{len(rows)} records...\n")
                            
                            if self.fs:
                                self.fs.write(f"    Successfully exported {len(rows)} records into {table}.\n")
                        else:
                            if self.fs:
                                self.fs.write(f"    No records found for {table}.\n")
                    except Exception as e:
                        if self.fs:
                            self.fs.write(f"    [!] Error processing {table}: {e}\n")
                        continue
                
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
                        missing = []
                        if 'ZTRANSFERT_0' not in columns: missing.append('ZTRANSFERT_0')
                        if 'ZTRANSDATE_0' not in columns: missing.append('ZTRANSDATE_0')
                        if 'UPDDATTIM_0' not in columns: missing.append('UPDDATTIM_0')
                        self.fs.write(f"[*] Table {table} is missing columns for incremental sync: {', '.join(missing)}. Skipping delta sync.\n")
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
        
        
              
            
        
        while self.running:
            with open(rf"{log_folder}\service_log.txt", "a") as f:
                site_config_dict = {}
                tables_to_sync = [
                    "SDELIVERY",
                    "SDELIVERYD",
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
                        "SORDERP",
                        "TABMODELIV",
                        

                    ]
        
  
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


                    site_config_conn = sqlite3.connect(db_path)
                    site_config_cursor = site_config_conn.cursor()
                    site_config_cursor.execute("SELECT * FROM site_configs") 
                    site_configs = site_config_cursor.fetchall()
                    site_config_conn.close()      

                    for site_config in site_configs:
                        site_config_dict[site_config[1]] = site_config[2]
                                
                    email_config = {
                        'smtp_server': email_rows[1],
                        'smtp_port': email_rows[4],
                        'smtp_username': email_rows[2],
                        'smtp_password': email_rows[3],
                        'from_email': email_rows[2],
                        'to_email': email_rows[5],
                        'subject': 'Database Sync Update'
                    }

                    f.write(f"[*] ====> Email sender {email_rows[2]} password {email_rows[3]} \n")
                    
                    parameters = {
                        "sites": ["AE011", "AE012"],
                        "site_dependent_tables": ["ITMFACILIT", "FACILITY"],
                        "site_keys_column": {"ITMFACILIT": "STOFCY_0", "FACILITY": "FCY_0"},
                        "primary_key_column": "AUUID_0", 
                        "all_tables": [t for t in tables_to_sync if t not in ["ITMFACILIT", "FACILITY"]],  # Exclude site-dependent
                        # "site_emails": {
                        #     "AE011": "angeldobaron@gmail.com",
                        #     "AE012": "chrisdobaron@gmail.com"
                        # }  
                        'site_emails' : site_config_dict
                    }

                    f.write(f"[*] =====> Site configs {site_config_dict} \n")
            
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

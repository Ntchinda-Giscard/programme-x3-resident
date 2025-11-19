
# import boto3
# from botocore.exceptions import ClientError
from typing import Optional
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
                    send_email(
                        email_receiver="gicardntchinda@gmail.com",
                        server=email_rows[1],
                        port=email_rows[4],  # Port fourni par l'utilisateur
                        email_sender=email_rows[2],
                        email_password=email_rows[5],
                        security=email_rows[6],  # "ssl", "tls", "both"
                        attachments=[
                            db_path_sqlite
                        ]
                    )
                    # upload_to_versioned_s3(
                    #     "pos-waza",
                    #     "uploads/sagex3_seed.db",
                    #     f"{folder_rows[1]}/sagex3_seed.db",
                    # )


                    # print(" All SEED tables copied successfully!")

                    f.write(f"Connected to obdc.\n {config_rows} dsn= {config_rows[1]}, username={config_rows[6]}, password={config_rows[7]}, database=x3waza ")
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

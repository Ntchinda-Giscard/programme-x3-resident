# import boto3
# from botocore.exceptions import ClientError
from typing import Any, Dict, List, Optional
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


LOCAL_DB_PATH = r"C:\poswaza\temp\db"
ZIP_FOLDER = r"C:\poswaza\temp\zip"



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
            with open(rf"{LOCAL_DB_PATH}\logs\service_log.txt", "a") as f:
                try:
                    db_path = rf"{LOCAL_DB_PATH}\config.db"

                    # config_conn = sqlite3.connect(db_path)
                    # config_cursor = config_conn.cursor()
                    # config_cursor.execute("SELECT * FROM database_configuration")
                    # config_rows = config_cursor.fetchone()
                    # config_conn.close()

                    # folder_conn = sqlite3.connect(db_path)
                    # folder_cursor = folder_conn.cursor()
                    # folder_cursor.execute("SELECT * FROM configurations_folders")
                    # folder_rows = folder_cursor.fetchone()
                    # folder_conn.close()


                    # email_conn = sqlite3.connect(db_path)
                    # email_cursor = email_conn.cursor()
                    # email_cursor.execute("SELECT * FROM email_configs")
                    # email_rows = email_cursor.fetchone()
                    # email_conn.close()


                    f.write("Service is running...\n")
                    # f.write(f"Connected to obdc.\n {config_rows} dsn= {config_rows[1]}, username={config_rows[6]}, password={config_rows[7]}, database=x3waza ")
                    # f.write(f"Email config: {email_rows}\n")
                except Exception as e:
                    f.write(f"Error in service execution: {e}\n")

            time.sleep(60)  # Wait 60 seconds before next loop

        servicemanager.LogInfoMsg("MyPythonService - Service stopped.")


# Exemple d'utilisation
    
if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)
    

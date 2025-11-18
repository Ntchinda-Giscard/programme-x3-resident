

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


import boto3
from botocore.exceptions import ClientError

def upload_to_versioned_s3(bucket_name, object_key, file_path,
                           aws_region="us-east-1",
                           aws_access_key_id="AKIAR2BMOVON3NQAL2UV",
                           aws_secret_access_key="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"):


    s3_client = boto3.client(
        "s3",
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    try:
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=open(file_path, "rb")
        )

        return {
            "ETag": response.get("ETag"),
            "VersionId": response.get("VersionId")
        }

    except ClientError as e:
        print(f"Error uploading file: {e}")
        return None



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
import os



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

                    sqlserver_conn = pyodbc.connect(
                        "DRIVER={ODBC Driver 17 for SQL Server};"
                        "SERVER=192.168.2.41,1433;"
                        "DATABASE=x3waza;"
                        "UID=superadmin;"
                        "PWD=MotDePasseFort123!;"
                    )

                    # sqlserver_conn = connect_to_database(
                    #     dsn= config_rows[1], database="x3waza", username=config_rows[6], password=config_rows[7])

                   
                    sqlserver_cursor = sqlserver_conn.cursor()
                    sqlite_conn = sqlite3.connect(f"{folder_rows[1]}/sagex3_seed.db", timeout=30, check_same_thread=False)
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
                        print(f" Processing table: SEED.{table}")

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

                        print(f" {table}: {len(rows)} rows copied.")

                    # --- Close connections ---
                    sqlserver_conn.close()
                    sqlite_conn.close()
                    print(" All SEED tables copied successfully!")

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


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonService)

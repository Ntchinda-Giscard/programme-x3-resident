def connect_to_database(dsn, database, tablename, email_field, username=None, password=None):
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
        cursor = conn.cursor()
        sql = f"SELECT {email_field} FROM {tablename}"
        cursor.execute(sql)
        rows = cursor.fetchall()
    
        return conn

    except pyodbc.Error as e:
        raise Exception(f"Failed to connect to database: {str(e)}")  



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


# LOG_FILE = "C:\\WAZAPOS_service_log.log"

# def log_message(message):
#     """Helper: log message with timestamp to file and Event Viewer"""
#     timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
#     line = f"{timestamp} {message}\n"

#     # Append to file
#     with open(LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(line)

#     # Send to Event Viewer
#     servicemanager.LogInfoMsg(line)


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
                    sqlserver_conn = pyodbc.connect(
                        "DRIVER={ODBC Driver 17 for SQL Server};"
                        "SERVER=192.168.2.41,1433;"
                        "DATABASE=x3waza;"
                        "UID=superadmin;"
                        "PWD=MotDePasseFort123!;"
                    )

                    # sqlserver_conn = connect_to_database(
                    #     dsn= config_rows[1],
                    #     username=config_rows[6],
                    #     password=config_rows[7],
                    #     database="x3waza"

                    # )
                    sqlserver_cursor = sqlserver_conn.cursor()
                    sqlite_conn = sqlite3.connect("c:/posdatabase/sagex3_seed.db", timeout=30, check_same_thread=False)
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

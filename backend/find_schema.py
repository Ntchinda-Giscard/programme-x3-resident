import pyodbc
import sys

def check_schemas():
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.2.41;DATABASE=x3waza;UID=wazapos;PWD=Passww0rd'
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        
        print("--- Checking All Schemas ---")
        cursor.execute("SELECT name FROM sys.schemas")
        for row in cursor.fetchall():
            print(f"Schema: {row.name}")
            
        print("\n--- Checking TABSDHTYP Location ---")
        cursor.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'TABSDHTYP'")
        results = cursor.fetchall()
        if not results:
            print("Table TABSDHTYP NOT FOUND in any schema!")
        for row in results:
            print(f"Table found in schema: {row.TABLE_SCHEMA}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schemas()

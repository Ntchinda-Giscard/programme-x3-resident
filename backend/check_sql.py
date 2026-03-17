import pyodbc

def check_db():
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.2.41;DATABASE=x3waza;UID=wazapos;PWD=Passww0rd'
    try:
        conn = pyodbc.connect(conn_str, timeout=30)
        cursor = conn.cursor()
        
        print("--- Checking Schemas ---")
        cursor.execute("SELECT name FROM sys.schemas")
        schemas = [row[0] for row in cursor.fetchall()]
        print(f"Schemas: {schemas}")
        
        print("\n--- Searching for TABSDHTYP ---")
        cursor.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%TABSDHTYP%'")
        tables = cursor.fetchall()
        for t in tables:
            print(f"Schema: {t[0]}, Table: {t[1]}")
            
        print("\n--- Checking Case Sensitivity ---")
        try:
            cursor.execute("SELECT * FROM [x3waza].[SEED].[TABSDHTYP] WHERE 1=0")
            print("Successfully accessed [x3waza].[SEED].[TABSDHTYP] (UPPERCASE)")
        except Exception as e:
            print(f"Failed to access [x3waza].[SEED].[TABSDHTYP]: {e}")
            
        try:
            cursor.execute("SELECT * FROM [x3waza].[seed].[TABSDHTYP] WHERE 1=0")
            print("Successfully accessed [x3waza].[seed].[TABSDHTYP] (lowercase)")
        except Exception as e:
            print(f"Failed to access [x3waza].[seed].[TABSDHTYP]: {e}")
            
        conn.close()
    except Exception as e:
        print(f"Global connection error: {e}")

if __name__ == '__main__':
    check_db()

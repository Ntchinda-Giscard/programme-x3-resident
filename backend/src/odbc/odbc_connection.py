import pyodbc

def connect_to_sql_server(server, database, username, password):
    connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    try:
        conn = pyodbc.connect(connection_string)
        print("Connection successful!")
        return conn
    except Exception as e:
        print(f"Error: {e}")
        return None

# Example usage
conn = connect_to_sql_server('192.168.2.41', 'x3waza', 'wazapos', 'Passw0rd')
if conn:
    conn.close()
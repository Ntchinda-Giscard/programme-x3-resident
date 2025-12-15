import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.41,1433;"
    "DATABASE=x3waza;"
    "UID=superadmin2;"
    "PWD=MotDePasseFort!2025"
)
print("Connection successful!")

# lzazwfuicxyvnsrx
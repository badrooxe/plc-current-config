import pyodbc
from datetime import datetime

# --------- Configuration ---------
SQL_SERVER = 'localhost'
SQL_USER = 'sa'
SQL_PASSWORD = '123'
DATABASE_NAME = 'Plc_DB'
TABLE_NAME = 'plc_data'

def insert_values_to_sql_server(extracted_values, config, timestamp):
    # --------- Connect to SQL Server Master ---------
    def get_master_connection():
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};UID={SQL_USER};PWD={SQL_PASSWORD};DATABASE=master"
        )
        return pyodbc.connect(conn_str, autocommit=True)

    # --------- Create Database If Not Exists ---------
    def create_database_if_needed():
        conn = get_master_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{DATABASE_NAME}')
            BEGIN CREATE DATABASE [{DATABASE_NAME}] END
        """)
        cursor.close()
        conn.close()

    # --------- Get Connection to Target DB ---------
    def get_database_connection():
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};UID={SQL_USER};PWD={SQL_PASSWORD};DATABASE={DATABASE_NAME}"
        )
        return pyodbc.connect(conn_str)

    # --------- Create Table If Not Exists ---------
    def create_table():
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            IF OBJECT_ID('{TABLE_NAME}', 'U') IS NULL
            BEGIN
                CREATE TABLE {TABLE_NAME} (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    description NVARCHAR(255),
                    value FLOAT,
                    extraction_time DATETIME
                )
            END
        """)
        conn.commit()
        cursor.close()
        conn.close()

    # Run setup steps
    create_database_if_needed()
    create_table()

    # --------- Insert Extracted Values Like Influx Format ---------
    conn = get_database_connection()
    cursor = conn.cursor()
    offsets_info = config.get("variables", {})

    for offset, info in offsets_info.items():
        val = extracted_values.get(offset, {}).get("value")
        if val is None:
            continue
        # Attempt to cast to float for SQL (In Influx this is dynamic)
        try:
            val_float = float(val)
        except Exception:
            print(f"⚠️ Could not convert value at offset {offset} to float: {val}")
            continue

        description = info.get("description", f"Offset_{offset}")
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (description, value, extraction_time)
            VALUES (?, ?, ?)
        """, (description, val_float, timestamp))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Inserted {len(extracted_values)} records into SQL Server table {TABLE_NAME}")
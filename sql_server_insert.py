import pyodbc
import time
from typing import Dict

# --------- Configuration ---------
SQL_SERVER = 'localhost'             # Change to your SQL Server instance
SQL_USER = 'sa'                      # SQL Server login
SQL_PASSWORD = 'YourStrong!Passw0rd' # Update accordingly
DATABASE_NAME = 'LiveDataDB'
TABLE_NAME = 'LiveReadings'

def PLC_to_SQL_Data(
# --------- Connect to SQL Server Master ---------
def get_master_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"DATABASE=master"
    )
    return pyodbc.connect(conn_str, autocommit=True)

# --------- Create New Database if Not Exists ---------
def create_database_if_needed():
    conn = get_master_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{DATABASE_NAME}')
        BEGIN
            CREATE DATABASE [{DATABASE_NAME}]
        END
    """)
    cursor.close()
    conn.close()

# --------- Connect to New Database ---------
def get_database_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"DATABASE={DATABASE_NAME}"
    )
    return pyodbc.connect(conn_str)

# --------- Create Table ---------
def create_table():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        IF OBJECT_ID('{TABLE_NAME}', 'U') IS NULL
        BEGIN
            CREATE TABLE {TABLE_NAME} (
                id INT IDENTITY(1,1) PRIMARY KEY,
                sensor_name VARCHAR(255),
                value FLOAT,
                extraction_time DATETIME DEFAULT GETDATE()
            )
        END
    """)
    conn.commit()
    cursor.close()
    conn.close()

# --------- Insert Row ---------
def insert_data(sensor_name: str, value: float, extraction_time: str = None):
    conn = get_database_connection()
    cursor = conn.cursor()
    if extraction_time:
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (sensor_name, value, extraction_time)
            VALUES (?, ?, ?)
        """, (sensor_name, value, extraction_time))
    else:
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (sensor_name, value)
            VALUES (?, ?)
        """, (sensor_name, value))
    conn.commit()
    cursor.close()
    conn.close()

# --------- Simulated Real-Time Loop ---------
def real_time_feed():
    data_stream = [
        {"sensor_name": "temp_sensor", "value": 22.5},
        {"sensor_name": "load_sensor", "value": 64.8},
        {"sensor_name": "temp_sensor", "value": 23.1}
    ]
    for data in data_stream:
        insert_data(**data)
        print(f"Inserted: {data}")
        time.sleep(1)  # Simulate 1-second real-time interval

# # --------- MAIN ---------
# if __name__ == "__main__":
#     create_database_if_needed()
#     create_table()
#     real_time_feed()  # Replace with your actual data source

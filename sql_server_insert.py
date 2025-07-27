# sql_server_insert.py

import logging
import pyodbc

def insert_values_to_sql_server(extracted_values, config, timestamp, db_number, sql_connection):
    """
    Inserts a batch of extracted PLC values into a SQL Server table.

    Args:
        extracted_values (dict): The data extracted from the PLC.
        config (dict): The configuration for the current DB.
        timestamp (datetime): The timestamp of the data extraction.
        db_number (int): The number of the data block.
        sql_connection (pyodbc.Connection): An active connection to the SQL Server database.
    """
    db_name = config.get("data_block_name", f"DB{db_number}")
    
    # Prepare a list of records for bulk insertion
    records_to_insert = []
    for offset_str, data in extracted_values.items():
        val = data.get("value")
        if val is None:
            continue
        
        # This tuple's order must match the columns in the INSERT statement below
        record = (
            timestamp,
            db_name,
            data.get("symbol", f"Offset_{offset_str}"),
            data.get("description", ""),
            str(val),  # Convert all values to string to fit in an NVARCHAR column
            data.get("unit", "")
        )
        records_to_insert.append(record)

    if not records_to_insert:
        print(f"⚠️  No records to write for {db_name} to SQL Server.")
        return

    # The SQL query for inserting data. 
    # Assumes a table named 'PLC_Data_Logs' exists.
    sql = """
    INSERT INTO PLC_Data_Logs 
    (LogTimestamp, DBName, Symbol, Description, Value, Unit) 
    VALUES (?, ?, ?, ?, ?, ?);
    """
    
    cursor = None
    try:
        cursor = sql_connection.cursor()
        # Use executemany for an efficient bulk insert
        cursor.executemany(sql, records_to_insert)
        sql_connection.commit()
        print(f"✅ Wrote {len(records_to_insert)} records for {db_name} to SQL Server.")
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"❌ Error writing to SQL Server for {db_name}. SQLSTATE: {sqlstate}. Error: {ex}")
    except Exception as e:
        logging.error(f"❌ An unexpected error occurred during SQL Server insertion for {db_name}: {e}")
    finally:
        if cursor:
            cursor.close()
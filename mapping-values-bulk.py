import logging
import os
import ctypes
import json
import re
import influxdb_client
import snap7
from snap7.util import *
from snap7.type import Areas
import time
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_insert import insert_values_to_influxdb
from sql_server_insert import insert_values_to_sql_server
import pyodbc

# ----------- Configuration ----------- #
PLC_IP = "192.0.0.2"
RACK = 0
SLOT = 0
CONFIG_FILE = "DBs_configurations/dbsConfig.json"  # Using the single consolidated file
DLL_PATH = os.path.abspath("snap7.dll")
token = os.environ.get("INFLUXDB_TOKEN", "1BOz9P_KlFRxnVx_F-vAKLif9EKCN4atknuxDSPCnSRhA_7Um1OjZR4AIBbHOTMd1ES0xs1uV05NbrbwG-pRsw==")
influx_client = InfluxDBClient(url="http://localhost:8086", token=token, org="plc")
conn_str = (
                r'DRIVER={ODBC Driver 17 for SQL Server};'
                r'SERVER=YOUR_SERVER_NAME;' # e.g., 'localhost' or 'SERVER\SQLEXPRESS'
                r'DATABASE=YOUR_DATABASE_NAME;'
                r'Trusted_Connection=yes;'
            )
sql_connection = pyodbc.connect(conn_str)



# ----------- DLL Load ----------- #
if not os.path.exists(DLL_PATH):
    raise FileNotFoundError("❌ snap7.dll not found. Please add it next to your script.")
ctypes.CDLL(DLL_PATH)


# ----------- Helper Functions ----------- #

def load_and_group_config(file_path):
    """
    Loads the consolidated JSON file, accesses the list under the "DBS" key,
    and groups the variables by their DB number.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Consolidated configuration file not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        print(f"✅ Loaded consolidated configuration from {file_path}")
    except Exception as e:
        print(f"❌ Failed to load or parse {file_path}: {e}")
        return {}

    # --- FIX IS HERE ---
    # The list of variables is inside the "DBS" key. We access it here.
    # .get('DBS', []) is a safe way to get the list, returning an empty list if 'DBS' doesn't exist.
    all_variables = config_data.get('DBS', [])
    if not all_variables:
        print("❌ The 'DBS' key was not found or its list is empty in the JSON file.")
        return {}
    # --- END OF FIX ---
    
    grouped_configs = {}
    processed_entries = set() # To handle duplicate variables gracefully

    for var in all_variables:
        try:
            match = re.search(r'DB(\d+)', var["Address/Identifier"])
            if not match:
                continue
            db_number = int(match.group(1))
            offset_str = str(var["OFSSET"])

            unique_key = (db_number, offset_str)
            if unique_key in processed_entries:
                continue
            processed_entries.add(unique_key)

            if db_number not in grouped_configs:
                grouped_configs[db_number] = {
                    "db_number": db_number,
                    "data_block_name": f"DB{db_number}",
                    "variables": {}
                }
            
            variable_info = {
                "symbol": var["Tag Name"],
                "description": var["Description"],
                "data_type": var["Data Type"],
                "unit": var["unit"]
            }

            if var["Data Type"] == "BOOLEEN" and '.' in offset_str:
                parts = offset_str.split('.')
                variable_info["byte_offset"] = int(parts[0])
                variable_info["bit_position"] = int(parts[1])
            
            grouped_configs[db_number]["variables"][offset_str] = variable_info

        except (KeyError, ValueError, TypeError) as e:
            logging.warning(f"Skipping malformed variable entry in config: {var}. Error: {e}")

    print(f"✅ Processed and grouped configuration for {len(grouped_configs)} unique DBs.")
    return grouped_configs


# ----------- PLC Analyzer Class ----------- #
class PLCAnalyzer:
    def __init__(self, ip, rack=0, slot=0):
        # The snap7.client.Client() object is not picklable, so it cannot be a class attribute if you use multiprocessing
        # For simplicity in this script, we create it here.
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot)
        if not self.client.get_connected():
            raise ConnectionError("❌ PLC connection failed")
        print(f"✅ Connected to PLC at {ip}")
        try:
                blocks = self.client.list_blocks()
                print("✅ Blocks found:")
                print(f"  OB:  {blocks.OBCount}")
                print(f"  FB:  {blocks.FBCount}")
                print(f"  FC:  {blocks.FCCount}")
                print(f"  SFB: {blocks.SFBCount}")
                print(f"  SFC: {blocks.SFCCount}")
                print(f"  DB:  {blocks.DBCount}")
                print(f"  SDB: {blocks.SDBCount}")
        except Exception as e:
                print(f"❌ Error listing blocks: {e}")


    def read_raw_db(self, db_number):
        try:
            return self.client.upload(db_number)
        except Exception as e:
            print(f"❌ Error reading DB{db_number}: {e}")
            return None

    def extract_specific_values_from_db(self, db_number, config):
        """Extracts specific values from a given DB using the provided configuration data."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}\nExtracting Values from DB{db_number} - {timestamp}\n{'='*60}")
        
        if not config or config.get("db_number") != db_number:
            print(f"❌ Invalid or missing DB{db_number} configuration.")
            return None

        raw_bytes = self.read_raw_db(db_number)
        if raw_bytes is None:
            print(f"❌ Failed to read DB{db_number}")
            return None
        
        print(f"DB{db_number} Size: {len(raw_bytes)} bytes")
        
        extracted_values = {}
        offsets_info = config["variables"]
        sorted_offsets = sorted(offsets_info.keys(), key=lambda x: float(x) if '.' in x else int(x))
        
        for offset_str in sorted_offsets:
            info = offsets_info[offset_str]
            symbol = info.get("symbol", "Unknown Symbol")
            data_type = info.get("data_type", "Unknown")
            byte_offset = int(float(offset_str))

            try:
                value = None
                if data_type == "VIRGULE_FLOTTANTE" and byte_offset + 4 <= len(raw_bytes):
                    value = get_real(raw_bytes, byte_offset)
                elif data_type in ["DWORD", "DUREE"] and byte_offset + 4 <= len(raw_bytes):
                    value = get_dword(raw_bytes, byte_offset)
                elif data_type == "DINT" and byte_offset + 4 <= len(raw_bytes):
                    value = get_dint(raw_bytes, byte_offset)
                elif data_type == "INT" and byte_offset + 2 <= len(raw_bytes):
                    value = get_int(raw_bytes, byte_offset)
                elif data_type in ["DEC", "WORD"] and byte_offset + 2 <= len(raw_bytes):
                    value = get_word(raw_bytes, byte_offset)
                elif data_type == "BYTE" and byte_offset + 1 <= len(raw_bytes):
                    value = get_byte(raw_bytes, byte_offset)
                elif data_type == "BOOLEEN":
                    b_offset = info.get("byte_offset", 0)
                    b_pos = info.get("bit_position", 0)
                    if b_offset < len(raw_bytes):
                        value = get_bool(raw_bytes, b_offset, b_pos)
                elif data_type in ["CARACTERE", "CARACTER"] and byte_offset + 1 <= len(raw_bytes):
                     value = get_char(raw_bytes, byte_offset)
                elif data_type == "HEXA" and byte_offset + 4 <= len(raw_bytes):
                    value = "0x" + raw_bytes[byte_offset:byte_offset+4].hex().upper()
                
                if value is not None:
                    extracted_values[offset_str] = { "value": value, **info }
                else:
                    logging.warning(f"Could not read {symbol} (Offset {offset_str}) due to insufficient data in DB.")

            except Exception as e:
                logging.error(f"Error extracting {symbol} (Offset {offset_str}): {e}", exc_info=True)
        
        self.export_extracted_values_to_file(extracted_values, config, timestamp)
        return extracted_values

    def export_extracted_values_to_file(self, extracted_values, config, timestamp, export_dir="dbs-dumps"):
        """Appends extracted values for a specific DB to a combined file."""
        os.makedirs(export_dir, exist_ok=True)
        output_file = f"{export_dir}/DBs_extracted_bulk_values.txt"
        db_number = config.get("db_number")
        db_name = config.get("data_block_name", f"DB{db_number}")

        try:
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n--- Extracted Values from {db_name} - {timestamp} ---\n")
                f.write("-" * 70 + "\n")
                for offset_str, data in extracted_values.items():
                    f.write(f"Offset {offset_str:>6}: {str(data['value']):<15} - {data['symbol']}\n")

            print(f"✅ Appended extracted values for {db_name} to {output_file}")

            token = os.environ.get("INFLUXDB_TOKEN", "1BOz9P_KlFRxnVx_F-vAKLif9EKCN4atknuxDSPCnSRhA_7Um1OjZR4AIBbHOTMd1ES0xs1uV05NbrbwG-pRsw==")
            if not token:
                raise ValueError("INFLUXDB_TOKEN is not set.")
            
            #here insert the values to InfluxDB function
            #bucket = "my-bucket"
            #org = "my-org"
            
            insert_values_to_influxdb(
                extracted_values=extracted_values,
                config=config,
                timestamp=datetime.utcnow(), # Pass the datetime object
                db_number=db_number,
                influx_client=influx_client,
                #bucket=bucket,
                #org=org
            )

            #here insert the values to SQL Server function
            
            insert_values_to_sql_server(
                extracted_values=extracted_values,
                config=config,
                timestamp=datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S"), # Convert string timestamp back to datetime
                db_number=db_number,
                sql_connection=sql_connection
            )

        except Exception as e:
            logging.error(f"Error exporting values for {db_name} to file: {e}", exc_info=True)


# ----------- Entry Point ----------- #
def main():
    analyzer = None
    try:
        all_db_configs = load_and_group_config(CONFIG_FILE)
        
        if not all_db_configs:
            print("❌ No valid configurations were loaded. Exiting.")
            return
            
        analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)

        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n--- Starting Data Extraction Cycle --- {timestamp} ---")

            for db_number, config_data in sorted(all_db_configs.items()):
                try:
                    analyzer.extract_specific_values_from_db(db_number, config_data)
                except Exception as e:
                    logging.error(f"A non-critical error occurred in the extraction loop for DB{db_number}: {e}", exc_info=True)

            print(f"\n--- Data Extraction Cycle Completed --- {timestamp} ---")
            print("⏳ Waiting 1 second before next cycle...")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️  Stopping data extraction program.")
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}", exc_info=True)
    finally:
        if analyzer and analyzer.client.get_connected():
            analyzer.client.disconnect()
            print("🔌 Disconnected from PLC.")
        if sql_connection:
            sql_connection.close()
            print("🔌 SQL Server connection closed.")
        print("✅ Program terminated.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
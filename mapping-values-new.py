import logging
import os
import ctypes
import json
import influxdb_client
import snap7
from snap7.util import *
from snap7.type import Areas
import time
from datetime import datetime
from influxdb_insert import insert_values_to_influxdb
from influxdb_client import InfluxDBClient


# ----------- Configuration ----------- #
PLC_IP = "192.0.0.2"
RACK = 0
SLOT = 0
DLL_PATH = os.path.abspath("snap7.dll")


# ----------- DLL Load ----------- #
if not os.path.exists(DLL_PATH):
    raise FileNotFoundError("❌ snap7.dll not found. Please add it next to your script.")

ctypes.CDLL(DLL_PATH)


# ----------- PLC Analyzer Class ----------- #
class PLCAnalyzer:
    def __init__(self, ip, rack=0, slot=0):
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
    
    def export_raw_to_file(self, db_number, raw_bytes, export_dir="dumps"):
        os.makedirs(export_dir, exist_ok=True)
        hex_str = raw_bytes.hex()
        with open(f"{export_dir}/DB{db_number}_raw.txt", "w") as f:
            f.write(hex_str)


    def scan_and_decode_db(self, db_number):
        print(f"\n{'='*60}\nScanning DB{db_number}\n{'='*60}")
        raw_bytes = self.read_raw_db(db_number)
        if raw_bytes is None:
            return

        print(f"Raw bytes read: {raw_bytes}")
        print(f"DB{db_number} Size: {len(raw_bytes)} bytes")
        print(f"Hex dump       : {raw_bytes.hex()}")
        self.export_raw_to_file(db_number, raw_bytes)

    def load_db_config(self, config_file_path):
        """Loads the DB configuration from a JSON file."""
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ Loaded DB configuration from {config_file_path}")
            return config
        except FileNotFoundError:
            print(f"❌ Error: Configuration file '{config_file_path}' not found.")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON in '{config_file_path}': {e}")
            return None
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            return None

    def extract_specific_values_from_db(self, db_number, config_file):
        """Extract specific values from a given DB using a configuration file and snap7 getters."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}\nExtracting Specific Values from DB{db_number} - {timestamp}\n{'='*60}")

        # Load configuration
        config = self.load_db_config(config_file)
        if not config or config.get("db_number") != db_number:
            print(f"❌ Invalid or missing DB{db_number} configuration.")
            logging.error(f"Invalid or missing DB{db_number} configuration.")
            return None # Return None to indicate failure

        offsets_info = config["variables"]

        # Read the specified DB
        raw_bytes = self.read_raw_db(db_number)
        if raw_bytes is None:
            print(f"❌ Failed to read DB{db_number}")
            logging.error(f"Failed to read DB{db_number}")
            return None # Return None to indicate failure

        print(f"DB{db_number} Size: {len(raw_bytes)} bytes")

        # Extract and display each value
        extracted_values = {}
        # Sort by offset for consistent output (handle DBX like "80.0" correctly)
        sorted_offsets = sorted(offsets_info.keys(), key=lambda x: float(x.split('.')[0]) if '.' in str(x) else int(x))
        
        for offset_str in sorted_offsets:
            # Handle DBX offsets like "80.0" (byte.bit)
            if '.' in str(offset_str):
                byte_offset = int(float(offset_str))
                # For display, we can keep the original string
                display_offset = offset_str 
            else:
                byte_offset = int(offset_str)
                display_offset = byte_offset
                
            info = offsets_info[offset_str]
            symbol = info.get("symbol", "Unknown Symbol")
            description = info.get("description", "No description")
            unit = info.get("unit", "")
            data_type = info.get("data_type", "Unknown")

            try:
                # --- Data Type Handling using snap7 getters ---
                
                # --- Floating Point ---
                if data_type == "VIRGULE_FLOTTANTE": # REAL (Single Precision Float)
                    if byte_offset + 4 <= len(raw_bytes):
                        value = get_real(raw_bytes, byte_offset) # Uses snap7.util.get_real
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value:12.3f} - {symbol} - {description}{unit_display}")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for VIRGULE_FLOTTANTE (REAL, 4 bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "DWORD": # 32-bit Unsigned Integer
                    if byte_offset + 4 <= len(raw_bytes):
                        value = get_dword(raw_bytes, byte_offset) # Uses snap7.util.get_dword
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value:12d} - {symbol} - {description}{unit_display} (DWORD)")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read DWORD from offset {display_offset} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for DWORD (4 bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "DINT": # 32-bit Signed Integer
                    if byte_offset + 4 <= len(raw_bytes):
                        value = get_dint(raw_bytes, byte_offset) # Uses snap7.util.get_dint
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value:12d} - {symbol} - {description}{unit_display} (DINT)")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read DINT from offset {display_offset} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for DINT (4 bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "INT": # 16-bit Signed Integer
                    if byte_offset + 2 <= len(raw_bytes): # INT is 2 bytes
                        value = get_int(raw_bytes, byte_offset) # Uses snap7.util.get_int
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value:12d} - {symbol} - {description}{unit_display} (INT)")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read INT from offset {display_offset} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for INT (2 bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "DEC" or data_type == "WORD": # 16-bit Unsigned Integer (DEC assumed to be WORD)
                    if byte_offset + 2 <= len(raw_bytes): # WORD is 2 bytes
                        value = get_word(raw_bytes, byte_offset) # Uses snap7.util.get_word
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value:12d} - {symbol} - {description}{unit_display} ({data_type})")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read {data_type} from offset {display_offset} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for {data_type} (2 bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "DUREE": # Duration (Assumed DWORD)
                    if byte_offset + 4 <= len(raw_bytes): # DUREE as DWORD (4 bytes)
                        value = get_dword(raw_bytes, byte_offset) # Uses snap7.util.get_dword
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value:12d} - {symbol} - {description}{unit_display} (DUREE)")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read DUREE from offset {display_offset} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for DUREE (4 bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "BYTE": # 8-bit Unsigned Integer
                    if byte_offset + 1 <= len(raw_bytes): # BYTE is 1 byte
                        value = get_byte(raw_bytes, byte_offset) # Uses snap7.util.get_byte
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value:12d} - {symbol} - {description}{unit_display} (BYTE)")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read BYTE from offset {display_offset} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for BYTE (1 byte) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "BOOLEEN":
                    # For BOOLEEN, use byte_offset and bit_position from config
                    bool_byte_offset = info.get("byte_offset", byte_offset)
                    bool_bit_position = info.get("bit_position", 0) # Default to bit 0 if not specified
                    if bool_byte_offset + 1 <= len(raw_bytes): # Need the byte containing the bit
                        value = get_bool(raw_bytes, bool_byte_offset, bool_bit_position) # Uses snap7.util.get_bool
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value!s:12} - {symbol} - {description}{unit_display} (BOOLEEN)")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read BOOLEEN from byte {bool_byte_offset}, bit {bool_bit_position} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for BOOLEEN (1 bit) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "CARACTER": # 8-bit Signed Integer (ASCII)
                    if byte_offset + 1 <= len(raw_bytes): # CARACTER is 1 byte
                        value = get_char(raw_bytes, byte_offset)
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {display_offset:>6}: {value!s:12} - {symbol} - {description}{unit_display} (CARACTER)")
                        extracted_values[offset_str] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                        logging.info(f"Read CARACTER from offset {display_offset} ({symbol})")
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for CARACTER (1 byte) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                elif data_type == "HEXA":
                    assumed_size = 4 # Default to 4 bytes, adjust if needed or add to config
                    if byte_offset + assumed_size <= len(raw_bytes):
                        # Extract bytes and format as hex string
                        hex_bytes = raw_bytes[byte_offset:byte_offset+assumed_size]
                        value_str = hex_bytes.hex().upper()
                        print(f"Offset {display_offset:>6}: 0x{value_str} - {symbol} - {description}")
                        extracted_values[offset_str] = {
                            "value": f"0x{value_str}",
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                    else:
                        msg = f"Offset {display_offset:>6}: Insufficient data (DB too small) for HEXA ({assumed_size} bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)
                # --- End Handling for known types ---
                else:
                    # Handle unknown or unexpected data types
                    msg = f"Offset {display_offset:>6}: Unsupported or unknown data type '{data_type}' found for symbol '{symbol}'. Skipping."
                    logging.warning(msg)
                    print(f"⚠️  {msg}")
                    # Optionally, include a placeholder entry
                    # extracted_values[offset_str] = {
                    #     "value": None,
                    #     "symbol": symbol,
                    #     "description": description,
                    #     "unit": unit,
                    #     "data_type": data_type,
                    #     "error": "Unsupported data type"
                    # }
                # --- End of Data Type Handling ---

            except Exception as e:
                # General exception handling for errors during reading/parsing
                error_msg = f"Offset {display_offset:>6}: Unexpected error extracting value ({symbol}, type: {data_type}): {e}"
                logging.error(error_msg, exc_info=True) # Log with traceback
                print(f"❌ {error_msg}")

        # Export to file - Pass the specific DB's data and config
        self.export_extracted_values_to_file(extracted_values, config, timestamp, db_number)
        return extracted_values


    # Inside your PLCAnalyzer class

    def export_extracted_values_to_file(self, extracted_values, config, timestamp, db_number, export_dir="dbs-dumps"):
        """Export extracted values for a specific DB to a combined readable file."""
        os.makedirs(export_dir, exist_ok=True)
        output_file = f"{export_dir}/DBs_extracted_values.txt"

        # Determine the DB name from the config or default to DB{db_number}
        db_name = config.get("data_block_name", f"DB{db_number}")

        try:
            # Open file in append mode to add data for each DB extraction
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n--- Extracted Values from {db_name} (DB{db_number}) - {timestamp} ---\n")
                f.write("-" * 60 + "\n")
                
                # Get the variables info from the config
                offsets_info = config["variables"]
                
                # Sort offsets for consistent output in the file
                sorted_offsets = sorted(offsets_info.keys(), key=lambda x: float(x.split('.')[0]) if '.' in str(x) else int(x))

                for offset_str in sorted_offsets:
                    info = offsets_info[offset_str]
                    symbol = info.get("symbol", "Unknown Symbol")
                    description = info.get("description", "No description")
                    unit = info.get("unit", "")
                    data_type = info.get("data_type", "Unknown")
                    
                    unit_display = f" ({unit})" if unit else ""
                    type_display = f" [{data_type}]" if data_type and data_type != "Unknown" else ""

                    if offset_str in extracted_values:
                        value_data = extracted_values[offset_str]
                        value = value_data.get("value")
                        
                        # Format value for display based on its type
                        if isinstance(value, float):
                            formatted_value = f"{value:12.3f}"
                        elif isinstance(value, int):
                            formatted_value = f"{value:12d}"
                        elif isinstance(value, str): # Covers HEXA and potential strings
                            formatted_value = f"{value:>12}"
                        elif isinstance(value, bool):
                            formatted_value = f"{str(value):>12}"
                        else: # None or other
                            formatted_value = f"{str(value):>12}"

                        f.write(f"Offset {offset_str:>6}: {formatted_value} - {symbol} - {description}{unit_display}{type_display}\n")
                    else:
                        f.write(f"Offset {offset_str:>6}: {'❌ Not extracted':>12} - {symbol} - {description}{unit_display}{type_display}\n")
                        
            print(f"✅ Appended extracted values for DB{db_number} to {output_file}")

            token = "1BOz9P_KlFRxnVx_F-vAKLif9EKCN4atknuxDSPCnSRhA_7Um1OjZR4AIBbHOTMd1ES0xs1uV05NbrbwG-pRsw=="
            if not token:
                raise ValueError("INFLUXDB_TOKEN environment variable not set")

            client = influxdb_client.InfluxDBClient(url="http://localhost:8086", token=token, org="plc-org")
            insert_values_to_influxdb(
                extracted_values,
                config,
                timestamp,
                db_number,
                influx_client=client,
                bucket="plc-data",
                org="plc-org"
            )

        except Exception as e:
            error_msg = f"Error exporting values for DB{db_number} to file: {e}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")

# ----------- Entry ----------- #
# def main():
#     analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)
    
#     # Continuous extraction every second
#     try:
#         while True:
#             analyzer.extract_specific_values_from_db102()
#             time.sleep(1)  # Wait 1 second before next extraction
#     except KeyboardInterrupt:
#         print("\n⏹️  Stopping data extraction...")
#         print("✅ Program terminated by user")


# if __name__ == "__main__":
#     main()

def main():
    analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)
    
    # Define the DBs and their corresponding configuration files
    # Ensure these paths are correct relative to where your script runs
    db_configs = [
        (100, "DBs_configurations/db100_config.json"),
        (101, "DBs_configurations/db101_config.json"),
        (102, "DBs_configurations/db102_config.json"), # Your existing config
        (103, "DBs_configurations/db103_config.json"),
        (104, "DBs_configurations/db104_config.json"),
        (105, "DBs_configurations/db105_config.json"),
        (106, "DBs_configurations/db106_config.json"),
        (108, "DBs_configurations/db108_config.json"),
        (376, "DBs_configurations/db376_config.json"),
        # Add more DBs and their config files here as needed
        # (DB_Number, "path/to/config_file.json")
    ]

    # Continuous extraction every second
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n--- Starting Data Extraction Cycle --- {timestamp} ---")
            
            # Iterate through each configured DB and extract its data
            for db_number, config_path in db_configs:
                if os.path.exists(config_path): # Check if config file exists before attempting
                    try:
                        print(f"\n-> Processing DB{db_number} using {config_path}")
                        analyzer.extract_specific_values_from_db(db_number, config_path)
                        # Optional: Add a very brief delay between DB reads if needed
                        # time.sleep(0.05) 
                    except Exception as e:
                        error_msg = f"❌ Error during extraction cycle for DB{db_number} ({config_path}): {e}"
                        print(error_msg)
                        logging.error(error_msg, exc_info=True) # Log with traceback
                else:
                    warning_msg = f"⚠️ Configuration file not found for DB{db_number}: {config_path}"
                    print(warning_msg)
                    logging.warning(warning_msg)
            
            print(f"\n--- Data Extraction Cycle Completed --- {timestamp} ---")
            print("⏳ Waiting 1 second before next cycle...")
            time.sleep(1)  # Wait 1 second before the next full cycle
            
    except KeyboardInterrupt:
        print("\n⏹️  Stopping continuous data extraction...")
        print("✅ Program terminated by user")
    except Exception as e:
        print(f"\n💥 Unexpected error in main loop: {e}")
        logging.critical(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        # Optional: Ensure resources are cleaned up if necessary
        # For example, disconnecting the PLC client if needed
        # if hasattr(analyzer, 'client') and analyzer.client.get_connected():
        #     analyzer.client.disconnect()
        #     print("🔌 PLC Client disconnected.")
        pass

if __name__ == "__main__":
    # Ensure the logging is configured if you are using it
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
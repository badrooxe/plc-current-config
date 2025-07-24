import logging
import os
import ctypes
import json
import snap7
from snap7.util import *
from snap7.type import Areas
import time
from datetime import datetime


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

    def extract_specific_values_from_db102(self,config_file="DBs_configurations/db102_config.json"):
        """Extract specific REAL values from DB102 at predefined offsets"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}\nExtracting Specific Values from DB102 - {timestamp}\n{'='*60}")

         # Load configuration
        config = self.load_db_config(config_file)
        if not config or config.get("db_number") != 102:
            print("❌ Invalid or missing DB102 configuration.")
            return
        
        offsets_info = config["variables"]
        
        # Read DB102
        raw_bytes = self.read_raw_db(102)
        if raw_bytes is None:
            print("❌ Failed to read DB102")
            return
            
        print(f"DB102 Size: {len(raw_bytes)} bytes")
        
        # Extract and display each value
        # extracted_values = {}
        # for offset, description in offsets_info.items():
        #     try:
        #         # Check if we have enough bytes
        #         if offset + 4 <= len(raw_bytes):
        #             # Extract REAL value at the specified offset
        #             real_value = get_real(raw_bytes, offset)
        #             extracted_values[offset] = real_value
        #             print(f"Offset {offset:3d}: {real_value:12.3f} - {description}")
        #         else:
        #             print(f"Offset {offset:3d}: ❌ Insufficient data (DB too small)")
        #     except Exception as e:
        #         print(f"Offset {offset:3d}: ❌ Error extracting value: {e}")
        
        # Extract and display each value
        extracted_values = {}
        # Sort by offset for consistent output
        sorted_offsets = sorted(offsets_info.keys(), key=int)
        for offset_str in sorted_offsets:
            offset = int(offset_str)
            info = offsets_info[offset_str]
            symbol = info.get("symbol", "Unknown Symbol")
            description = info.get("description", "No description")
            unit = info.get("unit", "")
            data_type = info.get("data_type", "Unknown")

            try:
                # --- Data Type Handling using snap7 getters ---
                # --- Floating Point ---
                if data_type == "VIRGULE_FLOTTANTE": # REAL (Single Precision Float)
                    if offset + 4 <= len(raw_bytes):
                        value = get_real(raw_bytes, offset) # Uses snap7.util.get_real
                        unit_display = f" ({unit})" if unit else ""
                        print(f"Offset {offset:4d}: {value:12.3f} - {symbol} - {description}{unit_display}")
                        extracted_values[offset] = {
                            "value": value,
                            "symbol": symbol,
                            "description": description,
                            "unit": unit,
                            "data_type": data_type
                        }
                    else:
                        msg = f"Offset {offset:4d}: Insufficient data (DB too small) for VIRGULE_FLOTTANTE (REAL, 4 bytes) - {symbol}"
                        print(f"❌ {msg}")
                        logging.warning(msg)

                # --- Integers ---
                elif data_type == "DWORD" or data_type == "DUREE": # 32-bit Unsigned Integer
                     if offset + 4 <= len(raw_bytes):
                         value = get_dword(raw_bytes, offset) # Uses snap7.util.get_dword
                         unit_display = f" ({unit})" if unit else ""
                         print(f"Offset {offset:4d}: {value:12d} - {symbol} - {description}{unit_display} (DWORD)")
                         extracted_values[offset] = {
                             "value": value,
                             "symbol": symbol,
                             "description": description,
                             "unit": unit,
                             "data_type": data_type
                         }
                         logging.info(f"Read DWORD from offset {offset} ({symbol})")
                     else:
                         msg = f"Offset {offset:4d}: Insufficient data (DB too small) for DWORD (4 bytes) - {symbol}"
                         print(f"❌ {msg}")
                         logging.warning(msg)
                elif data_type == "DINT": # 32-bit Signed Integer
                     if offset + 4 <= len(raw_bytes):
                         value = get_dint(raw_bytes, offset) # Uses snap7.util.get_dint
                         unit_display = f" ({unit})" if unit else ""
                         print(f"Offset {offset:4d}: {value:12d} - {symbol} - {description}{unit_display} (DINT)")
                         extracted_values[offset] = {
                             "value": value,
                             "symbol": symbol,
                             "description": description,
                             "unit": unit,
                             "data_type": data_type
                         }
                         logging.info(f"Read DINT from offset {offset} ({symbol})")
                     else:
                         msg = f"Offset {offset:4d}: Insufficient data (DB too small) for DINT (4 bytes) - {symbol}"
                         print(f"❌ {msg}")
                         logging.warning(msg)
                elif data_type == "INT": # 16-bit Signed Integer
                     if offset + 2 <= len(raw_bytes): # INT is 2 bytes
                         value = get_int(raw_bytes, offset) # Uses snap7.util.get_int
                         unit_display = f" ({unit})" if unit else ""
                         print(f"Offset {offset:4d}: {value:12d} - {symbol} - {description}{unit_display} (INT)")
                         extracted_values[offset] = {
                             "value": value,
                             "symbol": symbol,
                             "description": description,
                             "unit": unit,
                             "data_type": data_type
                         }
                         logging.info(f"Read INT from offset {offset} ({symbol})")
                     else:
                         msg = f"Offset {offset:4d}: Insufficient data (DB too small) for INT (2 bytes) - {symbol}"
                         print(f"❌ {msg}")
                         logging.warning(msg)
                elif data_type == "WORD": # 16-bit Unsigned Integer
                     if offset + 2 <= len(raw_bytes): # WORD is 2 bytes
                         value = get_word(raw_bytes, offset) # Uses snap7.util.get_word
                         unit_display = f" ({unit})" if unit else ""
                         print(f"Offset {offset:4d}: {value:12d} - {symbol} - {description}{unit_display} (WORD)")
                         extracted_values[offset] = {
                             "value": value,
                             "symbol": symbol,
                             "description": description,
                             "unit": unit,
                             "data_type": data_type
                         }
                         logging.info(f"Read WORD from offset {offset} ({symbol})")
                     else:
                          msg = f"Offset {offset:4d}: Insufficient data (DB too small) for WORD (2 bytes) - {symbol}"
                          print(f"❌ {msg}")
                          logging.warning(msg)

                # --- Bits/Booleans ---
                # Note: Reading BOOL requires bit position info, which isn't in the current JSON.
                # If added, logic would be: value = get_bool(raw_bytes, byte_offset, bit_position)

                # --- Bytes ---
                elif data_type == "BYTE": # 8-bit Unsigned Integer
                     if offset + 1 <= len(raw_bytes): # BYTE is 1 byte
                         value = get_byte(raw_bytes, offset) # Uses snap7.util.get_byte
                         unit_display = f" ({unit})" if unit else ""
                         print(f"Offset {offset:4d}: {value:12d} - {symbol} - {description}{unit_display} (BYTE)")
                         extracted_values[offset] = {
                             "value": value,
                             "symbol": symbol,
                             "description": description,
                             "unit": unit,
                             "data_type": data_type
                         }
                         logging.info(f"Read BYTE from offset {offset} ({symbol})")
                     else:
                          msg = f"Offset {offset:4d}: Insufficient data (DB too small) for BYTE (1 byte) - {symbol}"
                          print(f"❌ {msg}")
                          logging.warning(msg)

                elif data_type == "CARACTER": # 8-bit Signed Integer (ASCII)
                     if offset + 1 <= len(raw_bytes):
                            value = get_char(raw_bytes, offset) # Uses snap7.util.get_char
                            unit_display = f" ({unit})" if unit else ""
                            print(f"Offset {offset:4d}: '{value}' - {symbol} - {description}{unit_display} (CARACTER)")
                            extracted_values[offset] = {
                                "value": value,
                                "symbol": symbol,
                                "description": description,
                                "unit": unit,
                                "data_type": data_type
                            }
                            logging.info(f"Read CARACTER from offset {offset} ({symbol})")

                # --- Strings ---
                # Note: Reading strings requires knowing the maximum length.
                # This is complex from the current JSON. Example assumes length info is available.
                # elif data_type == "STRING":
                #      # Assume JSON has a 'string_length' field
                #      max_len = info.get("string_length", 254) # Default or get from config
                #      if offset + max_len + 2 <= len(raw_bytes): # STRING has 2 header bytes
                #          # snap7.util.get_string might need adjustment or use get_fstring
                #          # value = get_string(raw_bytes, offset) # Check snap7 docs
                #          # Or use get_fstring if length is fixed/truncated
                #          # value = get_fstring(raw_bytes, offset, max_len)
                #          # For now, placeholder
                #          value = "STRING_READING_LOGIC_NEEDED"
                #          print(f"Offset {offset:4d}: '{value}' - {symbol} - {description} (STRING)")
                #          extracted_values[offset] = { ... }
                #      else:
                #           msg = f"Offset {offset:4d}: Insufficient data for STRING (max {max_len} chars) - {symbol}"
                #           print(f"❌ {msg}")
                #           logging.warning(msg)

                # --- Hex/Other ---

                elif data_type == "DEC": # Decimal (assumed 4 bytes)
                     if offset + 4 <= len(raw_bytes):
                            value = get_real(raw_bytes, offset) # Uses snap7.util.get_real

                elif data_type == "HEXA":
                     if offset + 4 <= len(raw_bytes): # Assuming 4 bytes for HEXA, adjust if needed
                         # Extract bytes and format as hex string
                         hex_bytes = raw_bytes[offset:offset+4]
                         value_str = hex_bytes.hex().upper()
                         print(f"Offset {offset:4d}: 0x{value_str} - {symbol} - {description}")
                         extracted_values[offset] = {
                             "value": f"0x{value_str}",
                             "symbol": symbol,
                             "description": description,
                             "unit": unit,
                             "data_type": data_type
                         }
                     else:
                         msg = f"Offset {offset:4d}: Insufficient data (DB too small) for HEXA (assumed 4 bytes) - {symbol}"
                         print(f"❌ {msg}")
                         logging.warning(msg)
                # --- End Handling for known types ---
                else:
                    # Handle unknown or unexpected data types
                    msg = f"Offset {offset:4d}: Unsupported or unknown data type '{data_type}' found for symbol '{symbol}'. Skipping."
                    logging.warning(msg)
                    print(f"⚠️  {msg}")
                    # Optionally, include a placeholder entry
                    # extracted_values[offset] = {
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
                error_msg = f"Offset {offset:4d}: Unexpected error extracting value ({symbol}, type: {data_type}): {e}"
                logging.error(error_msg, exc_info=True) # Log with traceback
                print(f"❌ {error_msg}")
        # Export to file (you might want to modify export function signature)
        # self.export_extracted_values_to_file(extracted_values, offsets_info, timestamp)
        self.export_extracted_values_to_file(extracted_values, offsets_info, timestamp)

        return extracted_values


    def export_extracted_values_to_file(self, extracted_values, offsets_info, timestamp, export_dir="db-102-dumps"):
        """Export extracted values to a readable file"""
        os.makedirs(export_dir, exist_ok=True)
        
        with open(f"{export_dir}/DB102_extracted_values.txt", "a", encoding="utf-8") as f:
            f.write(f"\n\nExtracted Values from DB102 - {timestamp}\n")
            f.write("=" * 50 + "\n")
            
            for offset, description in offsets_info.items():
                if offset in extracted_values:
                    f.write(f"Offset {offset:3d}: {extracted_values[offset]:12.3f} - {description}\n")
                else:
                    f.write(f"Offset {offset:3d}: ❌ Not extracted - {description}\n")


# ----------- Entry ----------- #
def main():
    analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)
    
    # Continuous extraction every second
    try:
        while True:
            analyzer.extract_specific_values_from_db102()
            time.sleep(1)  # Wait 1 second before next extraction
    except KeyboardInterrupt:
        print("\n⏹️  Stopping data extraction...")
        print("✅ Program terminated by user")


if __name__ == "__main__":
    main()
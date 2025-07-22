# import snap7
# from snap7.type import Areas

# client = snap7.client.Client()
# client.connect('192.0.0.2', 0, 0)

# db_number = 99
# start = 0
# size = 16
# data = client.read_area(Areas.DB, db_number, start, size)

# print(f"Raw Bytes: {list(data)}")

# client.disconnect()
# -------------------------
# import snap7
# from snap7.util import *
# from snap7.type import Areas

# # Connect to the PLC
# client = snap7.client.Client()
# client.connect('192.0.0.2', 0, 0)  # Adjust IP, rack, slot

# # Read 16 bytes from DB1
# db_number = 1
# start = 0
# size = 16
# data = client.read_area(Areas.DB, db_number, start, size)

# # Parse INT at offset 0
# int_val = get_int(data, 0)

# # Parse REAL at offset 10
# real_val = get_real(data, 10)

# # Print values
# print(f"INT Value: {int_val}")
# print(f"REAL Value: {real_val}")

# client.disconnect()
# ---------------------------------------------------------
# import snap7
# from snap7.util import get_int, get_real
# from snap7.type import Areas

# PLC_IP    = '192.0.0.2'
# RACK      = 0
# SLOT      = 0
# START     = 0       # start byte in each DB
# SIZE      = 16      # bytes to read per DB
# INT_OFF   = 0       # INT offset
# REAL_OFF  = 10      # REAL offset

# def read_dbs():
#     client = snap7.client.Client()
#     client.connect(PLC_IP, RACK, SLOT)

#     for db_number in range(1, 501):
#         try:
#             data = client.read_area(Areas.DB, db_number, START, SIZE)
#         except Exception:
#             # DB doesn’t exist or access denied
#             continue

#         int_val  = get_int(data, INT_OFF)
#         real_val = get_real(data, REAL_OFF)

#         # Only show non-zero readings
#         if int_val != 0 or real_val != 0.0:
#             print(f"DB{db_number:03d} → INT: {int_val}, REAL: {real_val}")

#     client.disconnect()

# if __name__ == "__main__":
#     read_dbs()
# ------------------------------------------------
# ----------------------------------------
import snap7
from snap7.util import *
from snap7.type import Areas
import time

class S7DBDecoder:
    def __init__(self, ip='192.0.0.2', rack=0, slot=0):
        """Initialize S7 client connection"""
        self.client = snap7.client.Client()
        self.ip = ip
        self.rack = rack
        self.slot = slot
        
    def connect(self):
        """Connect to S7 PLC"""
        try:
            self.client.connect(self.ip, self.rack, self.slot)
            if self.client.get_connected():
                print(f"Connected to S7 PLC at {self.ip}")
                return True
            else:
                print("Failed to connect to S7 PLC")
                return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from S7 PLC"""
        if self.client.get_connected():
            self.client.disconnect()
            print("Disconnected from S7 PLC")
    
    def get_db_size(self, db_number):
        """Get the actual size of a DB by testing progressively larger reads"""
        try:
            # Try progressively larger reads to find actual size
            for size in [10, 50, 100, 500, 1000, 2000, 5000, 10000]:
                try:
                    data = self.client.read_area(Areas.DB, db_number, 0, size)
                    if not data:
                        return max(10, size - 100)  # Return previous working size
                except:
                    return max(10, size - 100)  # Return previous working size
            return 5000  # Default max if all reads succeed
        except:
            return None
    
    def read_raw_db(self, db_number, size=None, start_offset=0):
        """Read raw bytes from DB using read_area"""
        try:
            if size is None:
                size = self.get_db_size(db_number)
                if size is None:
                    return None
            
            raw_data = self.client.read_area(Areas.DB, db_number, start_offset, size)
            return raw_data
        except Exception as e:
            print(f"Error reading DB{db_number}: {e}")
            return None
    
    def decode_value(self, raw_bytes, data_type, offset=0, bit=None):
        """Decode raw bytes based on data type using snap7.util functions"""
        try:
            if data_type.upper() == 'INT':
                return get_int(raw_bytes, offset)
            elif data_type.upper() == 'DINT':
                return get_dint(raw_bytes, offset)
            elif data_type.upper() == 'REAL':
                return get_real(raw_bytes, offset)
            elif data_type.upper() == 'BOOL':
                if bit is not None:
                    return get_bool(raw_bytes, offset, bit)
                else:
                    return get_bool(raw_bytes, offset, 0)
            elif data_type.upper() == 'BYTE':
                return raw_bytes[offset] if offset < len(raw_bytes) else 0
            elif data_type.upper() == 'WORD':
                return get_word(raw_bytes, offset)
            elif data_type.upper() == 'DWORD':
                return get_dword(raw_bytes, offset)
            elif data_type.upper() == 'STRING':
                return get_string(raw_bytes, offset)
            else:
                return raw_bytes[offset:offset+4] if offset < len(raw_bytes) else b''
        except Exception as e:
            print(f"Error decoding {data_type} at offset {offset}: {e}")
            return None
    
    def auto_detect_and_decode(self, raw_bytes, start_offset=0, max_values=50):
        """
        Attempt to automatically detect and decode data types in raw bytes.
        This is heuristic-based since S7 doesn't provide type information.
        """
        decoded_data = []
        offset = start_offset
        value_count = 0
        
        while offset < len(raw_bytes) - 1 and value_count < max_values:
            # Skip if we don't have enough bytes
            if offset + 4 > len(raw_bytes):
                break
                
            # Try different data types and see what makes sense
            
            # 1. Try REAL (4 bytes) first - most specific
            if offset + 4 <= len(raw_bytes):
                try:
                    real_val = get_real(raw_bytes, offset)
                    # Check if it's a reasonable REAL value (not NaN, not too extreme)
                    if not (abs(real_val) > 1e10 or str(real_val) == 'nan' or str(real_val) == 'inf'):
                        # Additional check: if the value seems like a realistic measurement
                        if abs(real_val) < 1e6 and real_val != 0:
                            decoded_data.append({
                                'offset': offset,
                                'type': 'REAL',
                                'value': real_val,
                                'raw_bytes': raw_bytes[offset:offset+4].hex(),
                                'address': f'DB.DBD{offset}'
                            })
                            offset += 4
                            value_count += 1
                            continue
                except:
                    pass
            
            # 2. Try DINT (4 bytes)
            if offset + 4 <= len(raw_bytes):
                try:
                    dint_val = get_dint(raw_bytes, offset)
                    # Check if it's a reasonable DINT value and not zero
                    if -2147483648 <= dint_val <= 2147483647 and dint_val != 0:
                        decoded_data.append({
                            'offset': offset,
                            'type': 'DINT',
                            'value': dint_val,
                            'raw_bytes': raw_bytes[offset:offset+4].hex(),
                            'address': f'DB.DBD{offset}'
                        })
                        offset += 4
                        value_count += 1
                        continue
                except:
                    pass
            
            # 3. Try INT (2 bytes)
            if offset + 2 <= len(raw_bytes):
                try:
                    int_val = get_int(raw_bytes, offset)
                    # Check if it's a reasonable INT value and not zero
                    if -32768 <= int_val <= 32767 and int_val != 0:
                        decoded_data.append({
                            'offset': offset,
                            'type': 'INT',
                            'value': int_val,
                            'raw_bytes': raw_bytes[offset:offset+2].hex(),
                            'address': f'DB.DBW{offset}'
                        })
                        offset += 2
                        value_count += 1
                        continue
                except:
                    pass
            
            # 4. Try WORD (2 bytes)
            if offset + 2 <= len(raw_bytes):
                try:
                    word_val = get_word(raw_bytes, offset)
                    if word_val != 0:
                        decoded_data.append({
                            'offset': offset,
                            'type': 'WORD',
                            'value': word_val,
                            'raw_bytes': raw_bytes[offset:offset+2].hex(),
                            'address': f'DB.DBW{offset}'
                        })
                        offset += 2
                        value_count += 1
                        continue
                except:
                    pass
            
            # 5. Try BYTE (1 byte) - only if non-zero
            if offset < len(raw_bytes):
                byte_val = raw_bytes[offset]
                if byte_val != 0:
                    decoded_data.append({
                        'offset': offset,
                        'type': 'BYTE',
                        'value': byte_val,
                        'raw_bytes': raw_bytes[offset:offset+1].hex(),
                        'address': f'DB.DBB{offset}'
                    })
                offset += 1
                value_count += 1
        
        return decoded_data
    
    def decode_all_bools(self, raw_bytes, start_byte=0, num_bytes=4):
        """Decode all boolean values from specified bytes"""
        bool_data = []
        for byte_offset in range(start_byte, min(start_byte + num_bytes, len(raw_bytes))):
            for bit in range(8):
                try:
                    bool_val = get_bool(raw_bytes, byte_offset, bit)
                    if bool_val:  # Only show TRUE values
                        bool_data.append({
                            'offset': byte_offset,
                            'bit': bit,
                            'type': 'BOOL',
                            'value': bool_val,
                            'address': f'DB.DBX{byte_offset}.{bit}'
                        })
                except Exception as e:
                    print(f"Error reading BOOL at {byte_offset}.{bit}: {e}")
        return bool_data
    
    def decode_strings(self, raw_bytes, start_offset=0, max_strings=5):
        """Try to decode strings from raw bytes"""
        string_data = []
        offset = start_offset
        
        # S7 strings have a specific format: [max_length][actual_length][data...]
        for i in range(max_strings):
            if offset + 2 >= len(raw_bytes):
                break
            try:
                # Check if this looks like a string header
                max_len = raw_bytes[offset]
                actual_len = raw_bytes[offset + 1]
                
                if max_len > 0 and max_len < 255 and actual_len <= max_len and actual_len > 0:
                    string_val = get_string(raw_bytes, offset)
                    if string_val and len(string_val.strip()) > 0:  # Only non-empty strings
                        string_data.append({
                            'offset': offset,
                            'type': 'STRING',
                            'value': string_val,
                            'max_length': max_len,
                            'actual_length': actual_len,
                            'address': f'DB.DBB{offset}'
                        })
                    offset += max_len + 2  # Move past this string
                else:
                    offset += 10  # Move to next potential string location
            except:
                offset += 10
        
        return string_data
    
    def decode_common_types_at_offsets(self, raw_bytes, step=2):
        """Try common data types at regular offsets"""
        common_decodes = []
        
        # Try common data types at even offsets
        for offset in range(0, min(len(raw_bytes), 200), step):
            # INT (2 bytes)
            if offset + 2 <= len(raw_bytes):
                try:
                    int_val = get_int(raw_bytes, offset)
                    if int_val != 0:
                        common_decodes.append({
                            'offset': offset,
                            'type': 'INT',
                            'value': int_val,
                            'address': f'DB.DBW{offset}'
                        })
                except:
                    pass
            
            # REAL (4 bytes) - try at 4-byte aligned offsets
            if offset % 4 == 0 and offset + 4 <= len(raw_bytes):
                try:
                    real_val = get_real(raw_bytes, offset)
                    if real_val != 0 and not (abs(real_val) > 1e10 or str(real_val) in ['nan', 'inf']):
                        common_decodes.append({
                            'offset': offset,
                            'type': 'REAL',
                            'value': real_val,
                            'address': f'DB.DBD{offset}'
                        })
                except:
                    pass
            
            # DINT (4 bytes) - try at 4-byte aligned offsets  
            if offset % 4 == 0 and offset + 4 <= len(raw_bytes):
                try:
                    dint_val = get_dint(raw_bytes, offset)
                    if dint_val != 0:
                        common_decodes.append({
                            'offset': offset,
                            'type': 'DINT',
                            'value': dint_val,
                            'address': f'DB.DBD{offset}'
                        })
                except:
                    pass
        
        return common_decodes
    
    def scan_and_decode_db(self, db_number, detailed=False):
        """Scan and decode a single DB with multiple approaches"""
        print(f"\n{'='*60}")
        print(f"Scanning DB{db_number}")
        print(f"{'='*60}")
        
        # Read raw data
        raw_bytes = self.read_raw_db(db_number)
        if raw_bytes is None:
            print(f"Could not read DB{db_number}")
            return None
        
        print(f"DB{db_number} Size: {len(raw_bytes)} bytes")
        if detailed:
            print(f"Raw bytes (first 32): {raw_bytes[:32].hex()}")
        
        # Check if DB contains any non-zero data
        if all(b == 0 for b in raw_bytes):
            print(f"DB{db_number} contains only zeros - skipping detailed decode")
            return {'db_number': db_number, 'size': len(raw_bytes), 'has_data': False}
        
        result = {
            'db_number': db_number,
            'size': len(raw_bytes),
            'has_data': True,
            'raw_bytes': raw_bytes,
            'decoded_data': {},
        }
        
        # 1. Auto-detect and decode values (heuristic approach)
        print(f"\n--- Auto-detected Non-Zero Values ---")
        auto_decoded = self.auto_detect_and_decode(raw_bytes)
        if auto_decoded:
            result['decoded_data']['auto'] = auto_decoded
            for item in auto_decoded[:15]:  # Show first 15 values
                print(f"{item['address']:12s}: {item['type']:5s} = {item['value']} (raw: {item['raw_bytes']})")
        else:
            print("No significant auto-detected values found")
        
        # 2. Common types at regular offsets
        print(f"\n--- Common Types at Regular Offsets ---")
        common_decoded = self.decode_common_types_at_offsets(raw_bytes, step=2)
        non_zero_common = [item for item in common_decoded if item['value'] != 0]
        if non_zero_common:
            result['decoded_data']['common'] = non_zero_common
            for item in non_zero_common[:15]:  # Show first 15 non-zero values
                print(f"{item['address']:12s}: {item['type']:5s} = {item['value']}")
        else:
            print("No non-zero values found at common offsets")
        
        # 3. Boolean values (first few bytes)
        print(f"\n--- Boolean Values (TRUE only, first 8 bytes) ---")
        bool_data = self.decode_all_bools(raw_bytes, 0, 8)
        if bool_data:
            result['decoded_data']['booleans'] = bool_data
            for bool_item in bool_data:
                print(f"{bool_item['address']:12s}: {bool_item['value']}")
        else:
            print("No TRUE boolean values found in first 8 bytes")
        
        # 4. Try to decode strings
        print(f"\n--- String Values ---")
        string_data = self.decode_strings(raw_bytes)
        if string_data:
            result['decoded_data']['strings'] = string_data
            for string_item in string_data:
                print(f"{string_item['address']:12s}: STRING = '{string_item['value']}' (max:{string_item['max_length']}, len:{string_item['actual_length']})")
        else:
            print("No readable strings found")
        
        return result
    
    def scan_multiple_dbs(self, db_start=1, db_end=500, show_empty=False, detailed=False):
        """Scan multiple DBs and decode their contents"""
        print(f"Scanning DBs {db_start} to {db_end}...")
        print(f"Show empty DBs: {show_empty}")
        print(f"Detailed output: {detailed}")
        
        results = []
        dbs_with_data = 0
        accessible_dbs = 0
        
        for db_num in range(db_start, db_end + 1):
            try:
                # Quick check if DB exists by reading just 1 byte
                test_read = self.client.read_area(Areas.DB, db_num, 0, 1)
                if test_read is not None:
                    accessible_dbs += 1
                    result = self.scan_and_decode_db(db_num, detailed=detailed)
                    if result:
                        results.append(result)
                        if result['has_data']:
                            dbs_with_data += 1
                        elif show_empty:
                            print(f"DB{db_num}: Accessible but empty (all zeros)")
                
                # Small delay to avoid overwhelming the PLC
                time.sleep(0.05)
                
            except KeyboardInterrupt:
                print(f"\nScan interrupted at DB{db_num}")
                break
            except Exception as e:
                if detailed:
                    print(f"DB{db_num}: Not accessible - {e}")
        
        print(f"\n{'='*60}")
        print(f"SCAN SUMMARY")
        print(f"{'='*60}")
        print(f"DBs checked: {db_end - db_start + 1}")
        print(f"Accessible DBs: {accessible_dbs}")
        print(f"DBs with non-zero data: {dbs_with_data}")
        print(f"Empty DBs: {accessible_dbs - dbs_with_data}")
        
        return results

    def decode_specific_values(self, db_number, offset_type_pairs):
        """Decode specific known values from a DB"""
        print(f"\n--- Manual Decode for DB{db_number} ---")
        raw_data = self.read_raw_db(db_number)
        if raw_data is None:
            print(f"Could not read DB{db_number}")
            return None
        
        decoded_values = {}
        for offset, data_type, description in offset_type_pairs:
            try:
                if data_type.upper() == 'BOOL':
                    # For BOOL, offset format should be (byte_offset, bit_number)
                    byte_offset, bit_num = offset
                    value = get_bool(raw_data, byte_offset, bit_num)
                    address = f"DB{db_number}.DBX{byte_offset}.{bit_num}"
                else:
                    value = self.decode_value(raw_data, data_type, offset)
                    if data_type.upper() == 'INT':
                        address = f"DB{db_number}.DBW{offset}"
                    elif data_type.upper() in ['REAL', 'DINT', 'DWORD']:
                        address = f"DB{db_number}.DBD{offset}"
                    elif data_type.upper() in ['BYTE', 'STRING']:
                        address = f"DB{db_number}.DBB{offset}"
                    else:
                        address = f"DB{db_number}.DB{offset}"
                
                decoded_values[description] = {
                    'address': address,
                    'type': data_type.upper(),
                    'value': value
                }
                print(f"{address:15s}: {data_type:6s} = {value:>12} ({description})")
            except Exception as e:
                print(f"Error decoding {description} at offset {offset}: {e}")
        
        return decoded_values

# Example usage
if __name__ == "__main__":
    # Configuration - adjust for your setup
    PLC_IP = "192.0.0.2"  # Replace with your PLC IP
    RACK = 0
    SLOT = 0
    
    # Initialize decoder
    decoder = S7DBDecoder(PLC_IP, RACK, SLOT)
    
    try:
        # Connect to PLC
        if decoder.connect():
            
            # Option 1: Scan a single DB with detailed output
            print("=== SINGLE DB DETAILED SCAN ===")
            result = decoder.scan_and_decode_db(1, detailed=True)
            
            # Option 2: Scan multiple DBs (quick scan)
            print("\n\n=== MULTIPLE DB SCAN ===")
            results = decoder.scan_multiple_dbs(1, 10, show_empty=False, detailed=False)
            
            # Option 3: Manual decode specific values if you know the structure
            print("\n\n=== MANUAL SPECIFIC DECODES ===")
            # Example: decode specific known values from DB1
            specific_values = [
                (0, 'INT', 'Status Code'),
                (2, 'INT', 'Error Code'),
                (4, 'DINT', 'Counter Value'),
                (8, 'REAL', 'Temperature'),
                (12, 'REAL', 'Pressure'),
                ((16, 0), 'BOOL', 'Motor Running'),  # Byte 16, Bit 0
                ((16, 1), 'BOOL', 'Alarm Active'),   # Byte 16, Bit 1
                (20, 'STRING', 'Device Name')
            ]
            decoder.decode_specific_values(1, specific_values)
            
            # Option 4: Read raw data and decode manually
            print("\n\n=== RAW DATA MANUAL DECODE ===")
            raw_data = decoder.read_raw_db(1, size=50)  # Read first 50 bytes
            if raw_data:
                print(f"Raw data (50 bytes): {raw_data.hex()}")
                print(f"INT @0: {get_int(raw_data, 0)}")
                print(f"REAL @10: {get_real(raw_data, 10)}")
                print(f"BOOL @0.0: {get_bool(raw_data, 0, 0)}")
                print(f"DWORD @4: {get_dword(raw_data, 4)}")
            
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        print(f"Script error: {e}")
    finally:
        decoder.disconnect()
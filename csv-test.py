import snap7
from snap7.util import *
from snap7.type import Areas
import csv
import time
from datetime import datetime

def connect_plc(ip='192.0.0.2', rack=0, slot=0):
    """Connect to S7 PLC"""
    client = snap7.client.Client()
    try:
        client.connect(ip, rack, slot)
        if client.get_connected():
            print(f"Connected to PLC at {ip}")
            return client
        else:
            print("Failed to connect to PLC")
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def read_db_data(client, db_number, max_size=1000):
    """Read raw data from a DB"""
    try:
        # Try to read data, start with reasonable size
        raw_data = client.read_area(Areas.DB, db_number, 0, max_size)
        return raw_data
    except Exception as e:
        # Try smaller size if failed
        try:
            raw_data = client.read_area(Areas.DB, db_number, 0, 100)
            return raw_data
        except:
            return None

def decode_db_values(raw_data):
    """Decode common data types from raw bytes"""
    if not raw_data or len(raw_data) == 0:
        return {}
    
    decoded = {}
    
    # Try to decode common values at standard offsets
    try:
        # INTs every 2 bytes for first 20 bytes
        for i in range(0, min(20, len(raw_data)-1), 2):
            if i + 2 <= len(raw_data):
                val = get_int(raw_data, i)
                if val != 0:  # Only store non-zero values
                    decoded[f'INT_{i}'] = val
        
        # REALs every 4 bytes for first 40 bytes
        for i in range(0, min(40, len(raw_data)-3), 4):
            if i + 4 <= len(raw_data):
                val = get_real(raw_data, i)
                if val != 0 and not (abs(val) > 1e10 or str(val) in ['nan', 'inf']):
                    decoded[f'REAL_{i}'] = round(val, 4)
        
        # DINTs every 4 bytes for first 40 bytes
        for i in range(0, min(40, len(raw_data)-3), 4):
            if i + 4 <= len(raw_data):
                val = get_dint(raw_data, i)
                if val != 0:
                    decoded[f'DINT_{i}'] = val
        
        # BOOLs for first 4 bytes
        for byte_i in range(min(4, len(raw_data))):
            for bit in range(8):
                val = get_bool(raw_data, byte_i, bit)
                if val:  # Only store TRUE values
                    decoded[f'BOOL_{byte_i}_{bit}'] = val
                    
    except Exception as e:
        print(f"Error decoding data: {e}")
    
    return decoded

def export_dbs_to_csv(client, start_db=1, end_db=500, filename=None):
    """Export all DB data to CSV file"""
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"s7_dbs_export_{timestamp}.csv"
    
    print(f"Exporting DB{start_db} to DB{end_db} to {filename}")
    
    # Collect all data first to determine all possible columns
    all_data = []
    all_columns = set(['DB_Number', 'DB_Size', 'Has_Data', 'Timestamp'])
    
    for db_num in range(start_db, end_db + 1):
        try:
            # Read raw data
            raw_data = read_db_data(client, db_num)
            
            if raw_data is None:
                # DB not accessible
                row_data = {
                    'DB_Number': db_num,
                    'DB_Size': 0,
                    'Has_Data': False,
                    'Timestamp': datetime.now().isoformat()
                }
            else:
                # Check if DB has any non-zero data
                has_data = not all(b == 0 for b in raw_data)
                
                # Decode values
                decoded_values = decode_db_values(raw_data) if has_data else {}
                
                # Create row data
                row_data = {
                    'DB_Number': db_num,
                    'DB_Size': len(raw_data),
                    'Has_Data': has_data,
                    'Timestamp': datetime.now().isoformat()
                }
                
                # Add decoded values
                row_data.update(decoded_values)
                
                # Track all column names
                all_columns.update(decoded_values.keys())
            
            all_data.append(row_data)
            
            # Progress indicator
            if db_num % 50 == 0:
                print(f"Processed DB{db_num}...")
            
            # Small delay to avoid overwhelming PLC
            time.sleep(0.05)
            
        except KeyboardInterrupt:
            print(f"\nExport interrupted at DB{db_num}")
            break
        except Exception as e:
            print(f"Error processing DB{db_num}: {e}")
            # Add error row
            row_data = {
                'DB_Number': db_num,
                'DB_Size': -1,
                'Has_Data': False,
                'Timestamp': datetime.now().isoformat(),
                'Error': str(e)
            }
            all_data.append(row_data)
            all_columns.add('Error')
    
    # Sort columns for consistent output
    sorted_columns = sorted(all_columns)
    # Ensure key columns come first
    key_columns = ['DB_Number', 'DB_Size', 'Has_Data', 'Timestamp']
    for col in reversed(key_columns):
        if col in sorted_columns:
            sorted_columns.remove(col)
            sorted_columns.insert(0, col)
    
    # Write to CSV
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted_columns)
            writer.writeheader()
            
            for row in all_data:
                # Fill missing columns with empty values
                complete_row = {col: row.get(col, '') for col in sorted_columns}
                writer.writerow(complete_row)
        
        print(f"\nExport completed!")
        print(f"File: {filename}")
        print(f"Total DBs processed: {len(all_data)}")
        print(f"DBs with data: {sum(1 for row in all_data if row.get('Has_Data'))}")
        print(f"Total columns: {len(sorted_columns)}")
        
        return filename
        
    except Exception as e:
        print(f"Error writing CSV file: {e}")
        return None

def export_dbs_simple(client, start_db=1, end_db=500, filename=None):
    """Simple export - one row per DB with basic info and raw hex data"""
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"s7_dbs_simple_{timestamp}.csv"
    
    print(f"Simple export: DB{start_db} to DB{end_db} to {filename}")
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['DB_Number', 'Size', 'Has_Data', 'First_32_Bytes_Hex', 
                         'First_INT', 'First_REAL', 'Timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for db_num in range(start_db, end_db + 1):
                try:
                    raw_data = read_db_data(client, db_num, max_size=100)
                    
                    if raw_data is None:
                        # DB not accessible
                        row = {
                            'DB_Number': db_num,
                            'Size': 0,
                            'Has_Data': False,
                            'First_32_Bytes_Hex': '',
                            'First_INT': '',
                            'First_REAL': '',
                            'Timestamp': datetime.now().isoformat()
                        }
                    else:
                        has_data = not all(b == 0 for b in raw_data)
                        
                        # Get first INT and REAL if possible
                        first_int = ''
                        first_real = ''
                        try:
                            if len(raw_data) >= 2:
                                first_int = get_int(raw_data, 0)
                            if len(raw_data) >= 4:
                                first_real = round(get_real(raw_data, 0), 4)
                        except:
                            pass
                        
                        row = {
                            'DB_Number': db_num,
                            'Size': len(raw_data),
                            'Has_Data': has_data,
                            'First_32_Bytes_Hex': raw_data[:32].hex(),
                            'First_INT': first_int,
                            'First_REAL': first_real,
                            'Timestamp': datetime.now().isoformat()
                        }
                    
                    writer.writerow(row)
                    
                    # Progress indicator
                    if db_num % 100 == 0:
                        print(f"Processed DB{db_num}...")
                    
                    time.sleep(0.02)
                    
                except Exception as e:
                    print(f"Error with DB{db_num}: {e}")
                    row = {
                        'DB_Number': db_num,
                        'Size': -1,
                        'Has_Data': False,
                        'First_32_Bytes_Hex': f'ERROR: {str(e)}',
                        'First_INT': '',
                        'First_REAL': '',
                        'Timestamp': datetime.now().isoformat()
                    }
                    writer.writerow(row)
        
        print(f"\nSimple export completed: {filename}")
        return filename
        
    except Exception as e:
        print(f"Error creating CSV: {e}")
        return None

# Main execution
if __name__ == "__main__":
    # Configuration
    PLC_IP = "192.0.0.2"
    RACK = 0
    SLOT = 0
    DB_START = 1
    DB_END = 500
    
    # Connect to PLC
    client = connect_plc(PLC_IP, RACK, SLOT)
    
    if client:
        try:
            print("Choose export mode:")
            print("1. Detailed export (decode all data types)")
            print("2. Simple export (basic info + raw hex)")
            
            choice = input("Enter choice (1 or 2, default=2): ").strip()
            
            if choice == '1':
                # Detailed export
                filename = export_dbs_to_csv(client, DB_START, DB_END)
            else:
                # Simple export (default)
                filename = export_dbs_simple(client, DB_START, DB_END)
            
            if filename:
                print(f"\nData exported successfully to: {filename}")
            
        except KeyboardInterrupt:
            print("\nExport interrupted by user")
        except Exception as e:
            print(f"Export error: {e}")
        finally:
            if client.get_connected():
                client.disconnect()
                print("Disconnected from PLC")
    else:
        print("Could not connect to PLC")
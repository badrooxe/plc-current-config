import os
import ctypes
import platform
import snap7
from snap7.util import *
from snap7.type import Areas


# ----------- Configuration ----------- #
PLC_IP = "192.0.0.2"
RACK = 0
SLOT = 0
EXISTING_DBS = [100, 102, 103, 106, 108, 109, 111, 120,
              194, 500,
              201, 202, 208, 401, 402, 408, 411, 412, 419, 420]
#READ_SIZE = 64  # How many bytes to read per DB
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
                # Do NOT return anything
        except Exception as e:
                print(f"❌ Error listing blocks: {e}")


    def read_raw_db(self, db_number):  # Adjust READ_SIZE based on the client upload function
        try:
            #return self.client.read_area(Areas.DB, db_number, 0, size)
            return self.client.upload(Areas.DB, db_number)
        except Exception as e:
            print(f"❌ Error reading DB{db_number}: {e}")
            return None

    # def auto_detect_and_decode(self, raw_bytes):
    #     results = []
    #     for i in range(0, len(raw_bytes) - 4, 4):
    #         try:
    #             real_val = get_real(raw_bytes, i)
    #             dint_val = get_dint(raw_bytes, i)
    #             results.append({
    #                 'address': f'DB.DBD{i}',
    #                 'type': 'REAL',
    #                 'value': real_val,
    #                 'raw_bytes': raw_bytes[i:i+4].hex()
    #             })
    #             results.append({
    #                 'address': f'DB.DBD{i}',
    #                 'type': 'DINT',
    #                 'value': dint_val,
    #                 'raw_bytes': raw_bytes[i:i+4].hex()
    #             })
    #         except:
    #             continue
    #     return results

    # def decode_common_types_at_offsets(self, raw_bytes, step=2):
    #     results = []
    #     for i in range(0, len(raw_bytes) - 4, step):
    #         try:
    #             int_val = get_int(raw_bytes, i)
    #             real_val = get_real(raw_bytes, i)
    #             dint_val = get_dint(raw_bytes, i)
    #             results.extend([
    #                 {'address': f'DB.DBW{i}', 'type': 'INT', 'value': int_val},
    #                 {'address': f'DB.DBD{i}', 'type': 'REAL', 'value': real_val},
    #                 {'address': f'DB.DBD{i}', 'type': 'DINT', 'value': dint_val},
    #             ])
    #         except:
    #             continue
    #     return results

    # def decode_all_bools(self, raw_bytes, start_byte=0, length=8):
    #     results = []
    #     for byte_index in range(start_byte, start_byte + length):
    #         if byte_index >= len(raw_bytes):
    #             break
    #         byte_val = raw_bytes[byte_index]
    #         for bit in range(8):
    #             if (byte_val >> bit) & 1:
    #                 results.append({'address': f'DB.DBX{byte_index}.{bit}', 'value': True})
    #     return results

    # def decode_strings(self, raw_bytes):
    #     strings = []
    #     for i in range(len(raw_bytes) - 2):
    #         max_len = raw_bytes[i]
    #         actual_len = raw_bytes[i+1]
    #         if max_len > 0 and actual_len <= max_len:
    #             start = i + 2
    #             end = start + actual_len
    #             if end <= len(raw_bytes):
    #                 try:
    #                     val = raw_bytes[start:end].decode('ascii', errors='ignore')
    #                     strings.append({
    #                         'address': f'DB.DBB{i}',
    #                         'value': val,
    #                         'max_length': max_len,
    #                         'actual_length': actual_len
    #                     })
    #                 except:
    #                     continue
    #     return strings

    # def unified_decoder(self, raw_bytes):
    #     decoded = []
    #     size = len(raw_bytes)

    #     i = 0
    #     while i < size:
    #         # BOOL
    #         try:
    #             if raw_bytes[i] != 0:
    #                 decoded.append({"address": f"DB.DBX{i}", "type": "BOOL", "value": True})
    #         except:
    #             pass

    #         # INT
    #         if i + 1 < size:
    #             try:
    #                 val = get_int(raw_bytes, i)
    #                 if val != 0:
    #                     decoded.append({"address": f"DB.DBW{i}", "type": "INT", "value": val})
    #             except:
    #                 pass

    #         # DINT
    #         if i + 3 < size:
    #             try:
    #                 val = get_dint(raw_bytes, i)
    #                 if val != 0:
    #                     decoded.append({"address": f"DB.DBD{i}", "type": "DINT", "value": val})
    #             except:
    #                 pass

    #         # REAL
    #         if i + 3 < size:
    #             try:
    #                 val = get_real(raw_bytes, i)
    #                 if abs(val) > 0.0001:
    #                     decoded.append({"address": f"DB.DBD{i}", "type": "REAL", "value": round(val, 6)})
    #             except:
    #                 pass

    #         # STRING
    #         if i + 2 < size:
    #             try:
    #                 max_len = raw_bytes[i]
    #                 actual_len = raw_bytes[i + 1]
    #                 if actual_len > 0 and actual_len <= max_len and i + 2 + actual_len <= size:
    #                     string_val = raw_bytes[i + 2:i + 2 + actual_len].decode("utf-8", errors="ignore")
    #                     decoded.append({
    #                         "address": f"DB.DBW{i}",
    #                         "type": "STRING",
    #                         "value": string_val,
    #                         "max_length": max_len,
    #                         "actual_length": actual_len
    #                     })
    #             except:
    #                 pass

    #         i += 1

    #     return decoded
    
    def export_raw_to_file(self, db_number, raw_bytes, export_dir="dumps"):
        os.makedirs(export_dir, exist_ok=True)
        hex_str = raw_bytes.hex()
        with open(f"{export_dir}/DB{db_number}_raw.txt", "w") as f:
            f.write(hex_str)


    def scan_and_decode_db(self, db_number):
        print(f"\n{'='*60}\nScanning DB{db_number}\n{'='*60}")
        #raw_bytes = self.read_raw_db(db_number,READ_SIZE)
        raw_bytes = self.read_raw_db(db_number)
        if raw_bytes is None:
            return

        print(f"Raw bytes read: {raw_bytes}")
        print(f"DB{db_number} Size: {len(raw_bytes)} bytes")
        print(f"Hex dump       : {raw_bytes.hex()}")
        self.export_raw_to_file(db_number, raw_bytes)



    # ❗️For Testing One DB
    def test_single_db(self, db_number):
        return self.scan_and_decode_db(db_number, detailed=True)


# ----------- Entry ----------- #
def main():
    #single_db = PLCAnalyzer(PLC_IP, RACK, SLOT).test_single_db(103)
    analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)
    for db in EXISTING_DBS:
        analyzer.scan_and_decode_db(db, detailed=True)
    #return single_db


if __name__ == "__main__":
    main()

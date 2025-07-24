# import snap7
# from snap7.util import *
# from time import sleep

# PLC_IP = "192.0.0.2"  # Replace with your PLC IP

# def try_connect(ip, rack, slot):
#     client = snap7.client.Client()
#     try:
#         client.connect(ip, rack, slot)
#         if client.get_connected():
#             print(f"✅ Connected successfully: Rack={rack}, Slot={slot}")
#             client.disconnect()
#             return True
#     except Exception as e:
#         print(f"❌ Failed: Rack={rack}, Slot={slot} → {e}")
#     return False

# # Try common values
# for rack in range(0, 3):
#     for slot in range(0, 10):
#         print(f"Trying Rack={rack}, Slot={slot}")
#         if try_connect(PLC_IP, rack, slot):
#             exit(0)

# print("❌ No valid Rack/Slot combination found.")


import os
import ctypes
import snap7
from snap7.util import *
from snap7.type import Areas


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


    # def read_raw_db(self, db_number):
    #     try:
    #         return self.client.upload(Areas.DB, db_number)
    #     except Exception as e:
    #         print(f"❌ Error reading DB{db_number}: {e}")
    #         return None
    
    # def export_raw_to_file(self, db_number, raw_bytes, export_dir="dumps"):
    #     os.makedirs(export_dir, exist_ok=True)
    #     hex_str = raw_bytes.hex()
    #     with open(f"{export_dir}/DB{db_number}_raw.txt", "w") as f:
    #         f.write(hex_str)


    # def scan_and_decode_db(self, db_number):
    #     print(f"\n{'='*60}\nScanning DB{db_number}\n{'='*60}")
    #     raw_bytes = self.read_raw_db(db_number)
    #     if raw_bytes is None:
    #         return

    #     print(f"Raw bytes read: {raw_bytes}")
    #     print(f"DB{db_number} Size: {len(raw_bytes)} bytes")
    #     print(f"Hex dump       : {raw_bytes.hex()}")
    #     self.export_raw_to_file(db_number, raw_bytes)


# ----------- Entry ----------- #
def main():
    analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)
    return analyzer
    


if __name__ == "__main__":
    main()


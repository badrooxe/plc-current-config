import os
import ctypes
import platform

# Simple DLL loading
dll_path = os.path.abspath("snap7.dll")

# Check if DLL exists
if not os.path.exists(dll_path):
    print(f"❌ snap7.dll not found at: {dll_path}")
    print("📋 Please download snap7.dll and place it in the same folder as this script")
    exit(1)

# Check Python architecture
arch = platform.architecture()[0]
print(f"🔍 Python architecture: {arch}")

# Load the DLL
try:
    ctypes.CDLL(dll_path)
    print(f"✅ Successfully loaded snap7.dll")
except Exception as e:
    print(f"❌ Failed to load snap7.dll: {e}")
    print("📋 Make sure you have the 64-bit version for 64-bit Python")
    exit(1)

import snap7
from snap7.util import *
from snap7.type import Block,Area

def connect_to_plc(ip, rack=0, slot=0):
    plc = snap7.client.Client()
    try:
        plc.connect(ip, rack, slot)
        if plc.get_connected():
            print(f"✅ Connected to PLC at {ip}")
            print(plc.get_cpu_state()) # Print CPU state for debugging
        else:
            raise Exception("❌ Connection failed")
        return plc
    except Exception as e:
        print(f"❌ Connection error: {e}")
        raise

def list_all_blocks(plc):
    try:
        blocks = plc.list_blocks()
        print("✅ Blocks found:")
        print(f"  OB:  {blocks.OBCount}")
        print(f"  FB:  {blocks.FBCount}")
        print(f"  FC:  {blocks.FCCount}")
        print(f"  SFB: {blocks.SFBCount}")
        print(f"  SFC: {blocks.SFCCount}")
        print(f"  DB:  {blocks.DBCount}")
        print(f"  SDB: {blocks.SDBCount}")
        return blocks
    except Exception as e:
        print(f"❌ Error listing blocks: {e}")
        return None

# def read_db_info(plc):
#     print("\n🔍 Extracting DB block info...")
#     db_count = 0
#     for db_num in range(1, 283):  # Start from 1, as DB0 is usually system reserved
#         try:
#             block_info = plc.get_block_info(Block.DB, db_num)
#             area_info = plc.read_area(Area.DB, db_num, 0, 16)  # Read first 256 bytes of DB
#             print(f"📄 DB{db_num}: Size={block_info.MC7Size} bytes | Lang={block_info.Language} | Type={block_info.Type}")
#             print(f"📄 DB{db_num} Area Info: {area_info}")
#             db_count += 1
#         except Exception:
#             continue  # Skip if DB doesn't exist
    
#     if db_count == 0:
#         print("⚠️ No accessible DB blocks found")
#     else:
#         print(f"✅ Found {db_count} DB blocks")

def read_db_info(plc):
    print("\n🔍 Extracting DB block info...")
    db_count = 0
    for db_num in range(1, 283):  # we have 282 DBs
        try:
            block_info = plc.get_block_info(Block.DB, db_num)
            size = block_info.MC7Size
            if size == 0:
                continue  # Skip empty DBs

            size_to_read = min(size, 32)  # Read first 32 bytes or the full size if smaller
            area_info = plc.read_area(Area.DB, db_num, 0, size_to_read)

            print(f"📄 DB{db_num}: Size={size} bytes | Lang={block_info.Language} | Type={block_info.Type}")
            print(f"📦 DB{db_num} Data (first {size_to_read} bytes): {area_info.hex()}")
            db_count += 1
        except Exception as e:
            # Uncomment for debugging
            # print(f"❌ DB{db_num} error: {e}")
            continue
    
    if db_count == 0:
        print("⚠️ No accessible DB blocks found")
    else:
        print(f"✅ Found and read {db_count} DB blocks")


def main():
    try:
        plc = connect_to_plc("192.0.0.2")
        list_all_blocks(plc)
        read_db_info(plc)
        plc.disconnect()
        print("✅ Disconnected from PLC")
    except Exception as e:
        print(f"❌ Script failed: {e}")

if __name__ == "__main__":
    main()
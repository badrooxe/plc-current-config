import os
import ctypes
import platform
import datetime
import snap7
from snap7.util import *
from snap7.type import Block, Area
from pymongo import MongoClient

# ====== DLL SETUP ======
dll_path = os.path.abspath("snap7.dll")
if not os.path.exists(dll_path):
    print(f"❌ snap7.dll not found at: {dll_path}")
    exit(1)

arch = platform.architecture()[0]
print(f"🔍 Python architecture: {arch}")

try:
    ctypes.CDLL(dll_path)
    print(f"✅ Successfully loaded snap7.dll")
except Exception as e:
    print(f"❌ Failed to load snap7.dll: {e}")
    exit(1)

# ====== MongoDB SETUP ======
def get_mongo_collection():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["plc_data"]
    collection = db["raw_data"]
    return collection

# ====== PLC FUNCTIONS ======
def connect_to_plc(ip, rack=0, slot=0):
    plc = snap7.client.Client()
    try:
        plc.connect(ip, rack, slot)
        if plc.get_connected():
            print(f"✅ Connected to PLC at {ip}")
            print(plc.get_cpu_state())
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

def read_db_info(plc):
    print("\n🔍 Extracting DB block info...")
    db_count = 0
    mongo_collection = get_mongo_collection()

    for db_num in range(1, 283):
        try:
            block_info = plc.get_block_info(Block.DB, db_num)
            size = block_info.MC7Size
            if size == 0:
                continue

            size_to_read = min(size, 32)
            area_data = plc.read_area(Area.DB, db_num, 0, size_to_read)

            hex_data = area_data.hex()
            print(f"📄 DB{db_num}: Size={size} bytes | Type={block_info.Type}")
            print(f"📦 Data (first {size_to_read} bytes): {hex_data}")

            # Save to MongoDB
            record = {
                "db_number": db_num,
                "size_bytes": size,
                "read_size": size_to_read,
                "timestamp": datetime.datetime.utcnow(),
                "data_hex": hex_data
            }
            mongo_collection.insert_one(record)

            db_count += 1
        except Exception as e:
            continue

    if db_count == 0:
        print("⚠️ No accessible DB blocks found")
    else:
        print(f"✅ Found and saved {db_count} DB blocks to MongoDB")

# ====== MAIN ======
def main():
    try:
        plc = connect_to_plc("192.168.0.1")
        list_all_blocks(plc)
        #read_db_info(plc)
        plc.disconnect()
        print("✅ Disconnected from PLC")
    except Exception as e:
        print(f"❌ Script failed: {e}")

if __name__ == "__main__":
    main()

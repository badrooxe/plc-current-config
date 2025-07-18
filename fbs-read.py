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
from snap7.type import Block

def connect_to_plc(ip, rack=0, slot=0):
    plc = snap7.client.Client()
    try:
        plc.connect(ip, rack, slot)
        if plc.get_connected():
            print(f"✅ Connected to PLC at {ip}")
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

def read_fb_info(plc, max_fb=500):
    print("\n🔍 Extracting FB (Function Block) info...")
    fb_count = 0
    for fb_num in range(1, max_fb + 1):
        try:
            info = plc.get_block_info(Block.FB, fb_num)
            print(f"📄 FB{fb_num}: Size={info.MC7Size} bytes | Lang={info.Language} | Type={info.Type}")
            fb_count += 1
        except Exception:
            continue  # Skip if FB doesn't exist
    
    if fb_count == 0:
        print("⚠️ No accessible FB blocks found")
    else:
        print(f"✅ Found {fb_count} FB blocks")

def read_fc_info(plc, max_fc=200):
    print("\n🔍 Extracting FC (Function) info...")
    fc_count = 0
    for fc_num in range(1, max_fc + 1):
        try:
            info = plc.get_block_info(Block.FC, fc_num)
            print(f"📄 FC{fc_num}: Size={info.MC7Size} bytes | Lang={info.Language} | Type={info.Type}")
            fc_count += 1
        except Exception:
            continue  # Skip if FC doesn't exist
    
    if fc_count == 0:
        print("⚠️ No accessible FC blocks found")
    else:
        print(f"✅ Found {fc_count} FC blocks")

def main():
    try:
        plc = connect_to_plc("192.0.0.2")
        list_all_blocks(plc)
        
        # Read Function Blocks (FB) - You have 342 of them!
        read_fb_info(plc, max_fb=400)
        
        # Read Functions (FC) - You have 163 of them
        read_fc_info(plc, max_fc=200)
        
        plc.disconnect()
        print("✅ Disconnected from PLC")
    except Exception as e:
        print(f"❌ Script failed: {e}")

if __name__ == "__main__":
    main()
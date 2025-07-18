import snap7
from snap7.util import *
from time import sleep

PLC_IP = "192.0.0.2"  # Replace with your PLC IP

def try_connect(ip, rack, slot):
    client = snap7.client.Client()
    try:
        client.connect(ip, rack, slot)
        if client.get_connected():
            print(f"✅ Connected successfully: Rack={rack}, Slot={slot}")
            client.disconnect()
            return True
    except Exception as e:
        print(f"❌ Failed: Rack={rack}, Slot={slot} → {e}")
    return False

# Try common values
for rack in range(0, 3):
    for slot in range(0, 10):
        print(f"Trying Rack={rack}, Slot={slot}")
        if try_connect(PLC_IP, rack, slot):
            exit(0)

print("❌ No valid Rack/Slot combination found.")

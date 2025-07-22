# s7_crane_monitor.py
import snap7
import struct
import time
import csv
import os
from datetime import datetime

import os
import ctypes
import platform



# Simple DLL loading
dll_path = os.path.abspath("snap7.dll")
# Load the DLL
try:
    ctypes.CDLL(dll_path)
    print(f"✅ Successfully loaded snap7.dll")
except Exception as e:
    print(f"❌ Failed to load snap7.dll: {e}")
    print("📋 Make sure you have the 64-bit version for 64-bit Python")
    exit(1)

# =============================================
# Configuration
# =============================================
PLC_IP = '192.0.0.2'        # ← CHANGE TO YOUR PLC IP
RACK = 0
SLOT = 0
INTERVAL = 5                   # Read every 5 seconds
LOG_FILE = 'crane_monitor_log2.csv'

# Only monitor these DBs (active from your CSV)
ACTIVE_DBS = [100, 102, 103, 106, 108, 109, 111, 120,
              194, 500,
              201, 202, 208, 401, 402, 408, 411, 412, 419, 420]

client = snap7.client.Client()

# Helper functions
def read_real(data, offset):
    return struct.unpack('>f', data[offset:offset+4])[0]

def read_int(data, offset):
    return struct.unpack('>h', data[offset:offset+2])[0]

def read_dint(data, offset):
    return struct.unpack('>i', data[offset:offset+4])[0]


# =============================================
# Parse Data Blocks (Crane-Specific Logic)
# =============================================

def parse_db100(data):
    """Main process DB – hydraulic, temp, pressure"""
    try:
        return {
            "Hydraulic_Temp_C": round(read_real(data, 16), 1) if data[16] != 0 else None,
            "Hydraulic_Pressure_bar": round(read_real(data, 20), 1),
            "Error_Code": round(read_real(data, 24), 3),
            "Run_Hours": read_dint(data, 32),
            "Fault_Count": read_int(data, 36),
            "State_Word": hex(read_int(data, 30))
        }
    except:
        return {"Error": "ParseFailed"}

def parse_db102(data):
    """Speed setpoints"""
    return {
        "SP_Slew_Speed_deg_min": round(read_real(data, 0), 1),
        "SP_Hoist_Speed_m_min": round(read_real(data, 4), 1)
    }

def parse_db103(data):
    """Calibration offsets"""
    return {
        "Calib_LoadCell_A": round(read_real(data, 0), 3),
        "Calib_Inclinometer": round(read_real(data, 4), 3),
        "Offset_TankA": round(read_real(data, 8), 3)
    }

def parse_db106(data):
    """System status & counters"""
    return {
        "System_Enabled": round(read_real(data, 0), 3),
        "Motor_Speed_SP_rpm": round(read_real(data, 4), 1),
        "Total_Lifts": read_dint(data, 8),
        "Status_Word": read_int(data, 12)
    }

def parse_db108(data):
    """Timer presets (ms or sec)"""
    return {
        "Delay_Start_ms": read_int(data, 0),
        "Delay_Stop_ms": read_int(data, 2),
        "Timeout_Limit_ms": read_int(data, 4),
        "Current_State": read_int(data, 6),
        "Substep": read_int(data, 8),
        "Retries": read_int(data, 10)
    }

def parse_db109(data):
    """Aux timers / sequence steps"""
    return {
        "T_Preheat_ms": read_int(data, 0),
        "T_Hold_ms": read_int(data, 2),
        "T_Cool_ms": read_int(data, 4),
        "Mode_Code": read_int(data, 6),
        "Firmware_Version": read_int(data, 8)
    }

def parse_db111(data):
    """Large config values"""
    return {
        "Max_Energy_kWh": round(read_real(data, 0), 1),
        "Threshold_High": round(read_real(data, 4), 1),
        "Threshold_Low": round(read_real(data, 8), 1)
    }

def parse_db120(data):
    """Small analog input (e.g., level sensor)"""
    return {
        "Tank_Level_percent": round(read_real(data, 0), 1),
        "Filter_Status": read_int(data, 4)
    }

def parse_db194(data):
    """Recipe IDs – likely job modes"""
    ids = [read_int(data, i*2) for i in range(8)]
    return {f"Job_Mode_{i}": ids[i] for i in range(8)}

def parse_db500(data):
    """Order queue – starts at byte 8"""
    ids = [read_int(data, 8 + i*2) for i in range(8)]
    return {f"Order_{i}": ids[i] for i in range(8)}

def parse_cycle_log(data, label):
    """Batch/cycle logs: DB2xx, DB4xx"""
    return {
        "Cycle_ID": int(round(read_real(data, 0), 0)),
        "Param_A": round(read_real(data, 4), 3),
        "Param_B": round(read_real(data, 8), 3),
        "Param_C": round(read_real(data, 12), 3),
        "Param_D": round(read_real(data, 16), 3),
        "Param_E": round(read_real(data, 20), 3),
        "Param_F": round(read_real(data, 24), 3),
        "Param_G": round(read_real(data, 28), 3)
    }


# Main parser dispatcher
def parse_db(db_num, data):
    result = {'DB': db_num}
    try:
        if db_num == 100:
            result.update(parse_db100(data))
        elif db_num == 102:
            result.update(parse_db102(data))
        elif db_num == 103:
            result.update(parse_db103(data))
        elif db_num == 106:
            result.update(parse_db106(data))
        elif db_num == 108:
            result.update(parse_db108(data))
        elif db_num == 109:
            result.update(parse_db109(data))
        elif db_num == 111:
            result.update(parse_db111(data))
        elif db_num == 120:
            result.update(parse_db120(data))
        elif db_num == 194:
            result.update(parse_db194(data))
        elif db_num == 500:
            result.update(parse_db500(data))
        elif db_num in [201, 202, 208, 401, 402, 408, 411, 412, 419, 420]:
            result.update(parse_cycle_log(data, db_num))
        else:
            result['Raw_Hex'] = data.hex()[:32]
    except Exception as e:
        result['Error'] = str(e)
    return result


# =============================================
# Main Execution Loop
# =============================================

def main():
    client.connect(PLC_IP, RACK, SLOT)
    if not client.get_connected():
        print("❌ Failed to connect to PLC")
        return
    print(f"✅ Connected to TEREX Gottwald M996007 at {PLC_IP}")

    # Setup CSV logging
    fieldnames = ["Timestamp"]
    first_write = True
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    print(f"📊 Starting monitoring (polling every {INTERVAL}s). Press Ctrl+C to stop.\n")

    try:
        while True:
            row = {"Timestamp": datetime.now().isoformat()}
            for db in ACTIVE_DBS:
                try:
                    data = client.db_read(db, 0, 100)
                    parsed = parse_db(db, data)
                    for k, v in parsed.items():
                        if k != 'DB':
                            row[f"DB{db}_{k}"] = v
                except Exception as e:
                    row[f"DB{db}_Error"] = str(e)

            # Print snapshot
            ts = row["Timestamp"][:19]
            print(f"[{ts}]")
            for k, v in row.items():
                if k != "Timestamp" and v not in [None, '', 0, 0.0]:
                    print(f"  {k:<25} = {v}")
            print("─" * 60)

            # Save to CSV
            if first_write:
                fieldnames += sorted([k for k in row.keys() if k != "Timestamp"])
                with open(LOG_FILE, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                first_write = False

            with open(LOG_FILE, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(row)

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user.")
    finally:
        client.disconnect()
        print(f"🔌 Disconnected. Log saved to '{LOG_FILE}'")


if __name__ == "__main__":
    main()
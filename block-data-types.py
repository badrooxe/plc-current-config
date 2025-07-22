import os
import ctypes
import snap7
from snap7.util import get_real, get_int, get_dint
from snap7.type import Areas

# ----------- Configuration ----------- #
PLC_IP = "192.0.0.2"
RACK = 0
SLOT = 0
EXISTING_DBS = [100, 102, 103, 106, 108, 109, 111, 120,
                194, 500, 201, 202, 208, 401, 402, 408, 411, 412, 419, 420]
READ_SIZE = 64  # bytes per DB
DLL_PATH = os.path.abspath("snap7.dll")

# Load the Snap7 DLL
if not os.path.exists(DLL_PATH):
    raise FileNotFoundError("❌ snap7.dll not found. Please add it next to your script.")
ctypes.CDLL(DLL_PATH)

class PLCAnalyzer:
    def __init__(self, ip, rack=0, slot=0):
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot)
        if not self.client.get_connected():
            raise ConnectionError("❌ PLC connection failed")

    def read_raw_db(self, db_number, size=READ_SIZE):
        try:
            return self.client.read_area(Areas.DB, db_number, 0, size)
        except:
            return None

    def scan_and_decode_db(self, db_number):
        raw = self.read_raw_db(db_number)
        if not raw or all(b == 0 for b in raw):
            return []  # empty or all zeros ⇒ no types

        detected = set()

        # REAL & DINT auto‑detection
        for i in range(0, len(raw) - 4, 4):
            # if any non-zero byte in this word, assume both types present
            if raw[i:i+4] != b'\x00\x00\x00\x00':
                detected.update(['REAL', 'DINT'])

        # INT detection at 2‑byte offsets
        for i in range(0, len(raw) - 2, 2):
            if raw[i:i+2] != b'\x00\x00':
                detected.add('INT')

        # BOOL detection: any bit set in first byte region
        if any((b != 0) for b in raw[:8]):
            detected.add('BOOL')

        # STRING detection (simple TL‑format)
        for i in range(len(raw) - 2):
            max_len, actual_len = raw[i], raw[i+1]
            if 0 < actual_len <= max_len and i+2+actual_len <= len(raw):
                detected.add('STRING')
                break

        return list(detected)

def main():
    analyzer = PLCAnalyzer(PLC_IP, RACK, SLOT)
    return {db: analyzer.scan_and_decode_db(db) for db in EXISTING_DBS}

if __name__ == "__main__":
    result = main()
    print(result)  # e.g. {100: ['REAL','DINT'], 102: [...], ...}

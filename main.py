import snap7
from kafka import KafkaProducer
import json
import time

PLC_IP = '192.0.0.2'
RACK = 0
SLOT = 0

# KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']
# TOPIC = 'plc_realtime_data'

client = snap7.client.Client()
client.connect(PLC_IP, RACK, SLOT)
if not client.get_connected():
    raise Exception("Could not connect to PLC")
print(f"✅ Connected to PLC at {PLC_IP}")

all_blocks = client.list_blocks()
print(all_blocks)

# producer = KafkaProducer(
#     bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
#     value_serializer=lambda v: json.dumps(v).encode('utf-8')
# )

# def get_all_db_blocks():
#     """Retrieve all DB blocks with their size."""
#     all_blocks = client.db_list()  # returns list of S7BlockInfo
#     db_blocks = [b for b in all_blocks if b.Type == 'DB']
#     print(f"🔍 Found {len(db_blocks)} DB blocks")
#     for b in db_blocks:
#         print(f" - DB{b.Number} size={b.Size} bytes")
#     return db_blocks

# def read_db(db_number, size):
#     try:
#         return client.db_read(db_number, 0, size)
#     except Exception as e:
#         print(f"⚠️ Failed to read DB{db_number}: {e}")
#         return None

# def parse_db_data(db_num, db_bytes):
#     if not db_bytes:
#         return None
#     # Example parse: convert to hex string (replace with your own)
#     return db_bytes.hex()

# def main_loop():
#     db_blocks = get_all_db_blocks()
#     while True:
#         for block in db_blocks:
#             db_bytes = read_db(block.Number, block.Size)
#             if db_bytes:
#                 parsed = parse_db_data(block.Number, db_bytes)
#                 message = {
#                     "sensor": "S7-300",
#                     "db_number": block.Number,
#                     "timestamp": time.time(),
#                     "raw_data": list(db_bytes),
#                     "parsed_data": parsed
#                 }
#                 #producer.send(TOPIC, value=message)
#                 print(f"📤 Sent DB{block.Number} data")
#         # minimal delay for CPU breathing
#         # time.sleep(0.01)

# try:
#     main_loop()
# except KeyboardInterrupt:
#     print("⏹️ Stopped by user")
# finally:
#     #producer.flush()
#     #producer.close()
#     client.disconnect()

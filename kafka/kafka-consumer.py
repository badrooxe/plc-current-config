from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'plc_realtime_data',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='plc-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("🔎 Listening for PLC messages...")
for message in consumer:
    print(f"📥 Received: {message.value}")

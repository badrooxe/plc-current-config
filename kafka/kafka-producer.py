from kafka import KafkaProducer
import json
import time
import random  # Simulate PLC data

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def get_plc_data():
    # Simulated PLC data structure
    return {
        "sensor": "S7-300",
        "timestamp": time.time(),
        "values": {
            "temperature": round(random.uniform(20, 30), 2),
            "pressure": round(random.uniform(1.0, 2.0), 2)
        }
    }

print("🔄 Sending PLC data to Kafka topic 'plc_realtime_data'... Press CTRL+C to stop.")
try:
    while True:
        data = get_plc_data()
        producer.send('plc_realtime_data', value=data)
        print(f"✅ Sent: {data}")
        time.sleep(1)  # Adjust for our real sensor rate
except KeyboardInterrupt:
    print("\n⏹️ Stopped sending.")
    producer.close()

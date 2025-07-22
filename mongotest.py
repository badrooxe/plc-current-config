from pymongo import MongoClient
from datetime import datetime

# ✅ Connect to local MongoDB
client = MongoClient("mongodb://localhost:27017/")

# ✅ Select or create database and collection
db = client["plc_data"]
collection = db["raw_data"]

# ✅ Sample document
data = {
    "timestamp": datetime.strptime("2025-07-18T22:30:00Z", "%Y-%m-%dT%H:%M:%SZ"),
    "source": "S7-300",
    "sensor_id": "S1",
    "value": 45.7,
    "unit": "°C",
    "status": "OK"
}

# ✅ Insert the document
result = collection.insert_one(data)

# ✅ Print inserted ID
print("Inserted ID:", result.inserted_id)

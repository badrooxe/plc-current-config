# import random
# from influxdb_client import InfluxDBClient, Point, WritePrecision
# from influxdb_client.client.write_api import SYNCHRONOUS
# import os
# import time
# from datetime import datetime, timezone
# # 1) Configuration via environment or hard‑code for test
# INFLUX_URL   = os.getenv("INFLUXDB_URL",   "http://localhost:8086")
# INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "1BOz9P_KlFRxnVx_F-vAKLif9EKCN4atknuxDSPCnSRhA_7Um1OjZR4AIBbHOTMd1ES0xs1uV05NbrbwG-pRsw==")
# INFLUX_ORG   = os.getenv("INFLUXDB_ORG",   "plc-org")
# INFLUX_BUCKET= os.getenv("INFLUXDB_BUCKET","plc-data")

# # 2) Connect
# client   = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
# write_api= client.write_api(write_options=SYNCHRONOUS)

# # 3) Write 5 test points
# for i in range(999):
#     sensor_value = round(random.uniform(10.0, 100.0), 2)  
#     p = (
#         Point("test_measurement")       # <-- new measurement name
#         .tag("test_tag", "reddead")  # optional tag
#         .field("value", sensor_value)  # numeric field
#         .time(datetime.now(), WritePrecision.S)  # timestamp
#     )
#     write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
#     print(f"✅ Wrote point {i} {sensor_value}  to test_measurement")
#     print(f"✅ Wrote value {sensor_value} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#     time.sleep(1)  # space them out by 1s

# print("All test points written.")
import random
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import os
import time
from datetime import datetime, timezone
# 1) Configuration via environment or hard‑code for test
INFLUX_URL   = os.getenv("INFLUXDB_URL",   "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN", "1BOz9P_KlFRxnVx_F-vAKLif9EKCN4atknuxDSPCnSRhA_7Um1OjZR4AIBbHOTMd1ES0xs1uV05NbrbwG-pRsw==")
INFLUX_ORG   = os.getenv("INFLUXDB_ORG",   "plc-org")
INFLUX_BUCKET= os.getenv("INFLUXDB_BUCKET","plc-data")

# 2) Connect
client   = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api= client.write_api(write_options=SYNCHRONOUS)

# 3) Write 5 test points
for i in range(999):
    sensor_value = round(random.uniform(10.0, 100.0), 2)  
    p = (
        Point("test_measurement")       # <-- new measurement name
        .tag("test_tag", "reddead")  # optional tag
        .field("value", sensor_value)  # numeric field
        .time(datetime.utcnow(), WritePrecision.S)  # timestamp
    )
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    print(f"✅ Wrote point {i} {sensor_value}  to test_measurement")
    print(f"✅ Wrote value {sensor_value} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    time.sleep(1)  # space them out by 1s

print("All test points written.")

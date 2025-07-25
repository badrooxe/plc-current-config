# import influxdb_client, os, time
# from influxdb_client import InfluxDBClient, Point, WritePrecision
# from influxdb_client.client.write_api import SYNCHRONOUS

# token = os.environ.get("INFLUXDB_TOKEN")
# print("InfluxDB Token: ", token)
# org = "plc-org"
# url = "http://localhost:8086"

# client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
# print("pinging influxdb client : ",client.ping())

# bucket="plc-data"

# write_api = client.write_api(write_options=SYNCHRONOUS)
   
# for value in range(5):
#   point = (
#     Point("measurement1")
#     .tag("tagname1", "tagvalue1")
#     .field("field1", value)
#   )
#   write_api.write(bucket=bucket, org="plc-org", record=point)
#   time.sleep(1) # separate points by 1 second
# print("Data written to InfluxDB bucket successfully.")


# query_api = client.query_api()

# query1 = """from(bucket: "plc-data")
#  |> range(start: -10m)
#  |> filter(fn: (r) => r._measurement == "measurement1")"""
# tables1 = query_api.query(query1, org="plc-org")

# print("first Query results:")

# for table in tables1:
#   for record in table.records:
#     print(record)

# print("second Query results:")

# query2 = """from(bucket: "plc-data")
#   |> range(start: -10m)
#   |> filter(fn: (r) => r._measurement == "measurement1")
#   |> mean()"""
# tables2 = query_api.query(query2, org="plc-org")

# for table in tables2:
#     for record in table.records:
#         print(record)


from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

def insert_values_to_influxdb(extracted_values, config, timestamp, db_number,
                              influx_client, bucket, org):
    # Single connectivity check (move this outside if you call in a loop)
    if not influx_client.ping():
        raise ConnectionError("Cannot reach InfluxDB – check URL/token/org")

    write_api    = influx_client.write_api(write_options=SYNCHRONOUS)
    db_name      = config.get("data_block_name", f"DB{db_number}")
    measurement  = config.get("measurement", "plc_data")
    offsets_info = config.get("variables", {})

    # Normalize timestamp to a UTC datetime
    extraction_time = (
        timestamp
        if isinstance(timestamp, datetime)
        else datetime.fromisoformat(timestamp)
    )

    points = []
    for offset, info in offsets_info.items():
        val = extracted_values.get(offset, {}).get("value")
        if val is None:
            continue

        # Build a Point with dynamic measurement
        point = (
            Point(measurement)
            .tag("db_name", db_name)
            .tag("symbol", info.get("symbol", f"Offset_{offset}"))
            .field("value", float(val) if isinstance(val, (int, float)) else str(val))
            .time(extraction_time, WritePrecision.S)
        )
        points.append(point)

    # Debug: see how many points we built
    print(f"🔍 Built {len(points)} points for measurement '{measurement}'")

    if not points:
        print(f"⚠️  No data to write for {db_name}, skipping")
        return

    # Write batch and report
    try:
        write_api.write(bucket=bucket, org=org, record=points)
        print(f"✅ Wrote {len(points)} points to '{measurement}' in bucket '{bucket}'")
    except Exception as e:
        print(f"❌ Error writing to InfluxDB: {e}")
        raise

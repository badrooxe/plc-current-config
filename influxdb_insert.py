from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

def insert_values_to_influxdb(extracted_values, config, timestamp, db_number, influx_client):
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    bucket = config.get("bucket", "my-bucket")
    org = config.get("org", "my-org")
    db_name = config.get("data_block_name", f"DB{db_number}")
    offsets_info = config.get("variables", {})

    # Sanity‑check connection
    if not influx_client.ping():
        print("❌ Cannot reach InfluxDB – check URL/token/org")
        return

    # Build points
    points = []
    extraction_time = (timestamp)
    for offset, info in offsets_info.items():
        val = extracted_values.get(offset, {}).get("value")
        if val is None:
            continue
        point = (
            Point("plc_data")
            .tag("db_name", db_name)
            .tag("symbol", info.get("symbol", f"Offset_{offset}"))
            .field("value", val)
            .tag("offset", offset)
            .tag("data_type", info.get("data_type", "unknown"))
            .tag("unit", info.get("unit", ""))
            .tag("description", info.get("description", ""))
            .time(extraction_time, WritePrecision.S)
        )
        points.append(point)

    # Skip empty batches
    if not points:
        print(f"⚠️  No data to write for {db_name}, skipping InfluxDB write")
        return

    # Write and report
    try:
        write_api.write(bucket=bucket, org=org, record=points)
        print(f"✅ Wrote {len(points)} points for {db_name} to InfluxDB")
    except Exception as e:
        print(f"❌ Error writing to InfluxDB: {e}")

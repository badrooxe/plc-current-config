from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

def insert_values_to_influxdb(extracted_values, config, timestamp, db_number, influx_client, bucket, org):
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    db_name = config.get("data_block_name", f"DB{db_number}")
    offsets_info = config.get("variables", {})

    # Sanity‑check connection
    if not influx_client.ping():
        print("❌ Cannot reach InfluxDB – check URL/token/org")
        return

    # Build points
    points = []
    extraction_time = (timestamp 
                       if isinstance(timestamp, datetime) 
                       else datetime.fromisoformat(timestamp))
    for offset, info in offsets_info.items():
        val = extracted_values.get(offset, {}).get("value")
        if val is None:
            continue
        point = (
            Point("plc_data")
            .tag("db_name", db_name)
            .tag("symbol", info.get("symbol", f"Offset_{offset}"))
            .field("value", float(val) if isinstance(val, (int, float)) else str(val))
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

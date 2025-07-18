from kafka.admin import KafkaAdminClient, NewTopic

# Connect to Kafka broker (relies on Kafka and Zookeeper being up)
admin_client = KafkaAdminClient(
    bootstrap_servers="localhost:9092",
    client_id='plc-data-pipeline-admin'
)

# Define topic configuration
topic_name = "plc_realtime_data"
topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)

# Create the topic
try:
    admin_client.create_topics(new_topics=[topic], validate_only=False)
    print(f"✅ Topic '{topic_name}' created successfully.")
except Exception as e:
    print(f"❌ Failed to create topic '{topic_name}': {str(e)}")
# Close the admin client connection
finally:
    admin_client.close()
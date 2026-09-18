import os

from kafka import KafkaAdminClient

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_ADMIN_USERNAME = os.getenv("KAFKA_ADMIN_USERNAME")
KAFKA_ADMIN_PASSWORD = os.getenv("KAFKA_ADMIN_PASSWORD")




admin = KafkaAdminClient(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
        client_id='admin_client_tasks',
        security_protocol='SASL_PLAINTEXT',
        sasl_mechanism='SCRAM-SHA-512',
        sasl_plain_username=KAFKA_ADMIN_USERNAME,
        sasl_plain_password=KAFKA_ADMIN_PASSWORD,
)


#List Topics
admin.list_topics()


#CREATE_TOPICS
def create_topics(topics_names: list[str], num_partitions: int, num_replication:int):

    existing_topics = admin.list_topics()

    for topic in topics_names:
        if topic in existing_topics:
            print(f"Topic '{topic}' already exists.")
            continue

        admin.create_topics(
            {
                topic: {
                    "num_partitions": num_partitions,
                    "replication_factor": num_replication
                    }
                    }
                    )

        return f"Topic(s) {', '.join(topics_names)} created successfully."


def delete_topics(topics_names: list[str]):

    existing_topics = admin.list_topics()

    for topic in topics_names:
        if topic not in existing_topics:
            print(f"Topic '{topic}' does not exist.")
            continue
        admin.delete_topics(
            [topic]
        )

        return f"Topic(s) {', '.join(topics_names)} deleted successfully."

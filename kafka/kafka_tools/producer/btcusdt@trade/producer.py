import json
import logging
import os
import time

import websocket
from avro_serialization import create_avro_serializer, to_trade_record
from prometheus_client import start_http_server
from prometheus_metrics import ProducerMetrics

from kafka import KafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "8000"))
logger = logging.getLogger(__name__)


# BINANCE SETTINGS
TICKER = "btcusdt@trade"
BINANCE_WS = f"wss://stream.binance.com:9443/ws/{TICKER}"
TRADE_TOPIC = "binance-btcusdt-trade"

producer_metrics = ProducerMetrics.create()
binance_producer: KafkaProducer


def create_producer() -> KafkaProducer:
    producer_config = {
        "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS.split(","),
        "security_protocol": "SASL_PLAINTEXT",
        "sasl_mechanism": "SCRAM-SHA-512",
        "sasl_plain_username": KAFKA_USERNAME,
        "sasl_plain_password": KAFKA_PASSWORD,
        "client_id": "binance-btcusdt-streaming",
        "value_serializer": create_avro_serializer(TRADE_TOPIC),
    }
    return KafkaProducer(**producer_config)


def on_open(ws) -> None:
    producer_metrics.connection_opened()


def on_close(ws, close_status_code, close_msg) -> None:
    producer_metrics.connection_closed()


def on_message(ws, message) -> None:

    # Prometheus Metrics: number of messages being received
    producer_metrics.messages_received.inc()

    started_at = time.perf_counter()

    try:
        payload = json.loads(message)
        metadata = binance_producer.send(
            TRADE_TOPIC,
            value=to_trade_record(payload),
        ).get(timeout=10)

        # Prometheus Metrics: number of messages being produced
        producer_metrics.messages_produced.inc()
        print(
            f"saved: topic={metadata.topic}, "
            f"partition={metadata.partition}, offset={metadata.offset}"
        )
    except Exception:

        # Prometheus Metrics: on exceptions, number of messages with errors
        producer_metrics.produce_errors.inc()
        logger.exception("Kafka did not save the Binance message")
    finally:

        # Prometheus Metrics: at the end of the process, time spent processing and
        # sending a message
        producer_metrics.produce_latency.observe(
            time.perf_counter() - started_at
        )


def main() -> None:
    global binance_producer

    start_http_server(PROMETHEUS_PORT)
    binance_producer = create_producer()

    ws = websocket.WebSocketApp(
        BINANCE_WS,
        on_open=on_open,
        on_close=on_close,
        on_message=on_message,
    )
    ws.run_forever()


if __name__ == "__main__":
    main()

import logging
import os
import time
from dataclasses import dataclass

import websocket
from kafka import KafkaProducer
from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD")
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "8000"))
logger = logging.getLogger(__name__)


#BINANCE SETTINGS
TICKER = "btcusdt@trade"
BINANCE_WS = f"wss://stream.binance.com:9443/ws/{TICKER}"




@dataclass
class ProducerMetrics:
    messages_received: Counter
    messages_produced: Counter
    produce_errors: Counter
    produce_latency: Histogram
    websocket_connected: Gauge
    websocket_disconnects: Counter
    websocket_reconnects: Counter
    _has_connected: bool = False

    @classmethod
    def create(
        cls,
        registry: CollectorRegistry | None = None,
    ) -> "ProducerMetrics":
        metrics_registry = registry if registry is not None else REGISTRY
        return cls(
            messages_received=Counter(
                "binance_messages_received_total",
                "Binance WebSocket messages received.",
                registry=metrics_registry,
            ),
            messages_produced=Counter(
                "kafka_messages_produced_total",
                "Messages successfully produced to Kafka.",
                registry=metrics_registry,
            ),
            produce_errors=Counter(
                "kafka_produce_errors_total",
                "Kafka produce operations that failed.",
                registry=metrics_registry,
            ),
            produce_latency=Histogram(
                "kafka_produce_latency_seconds",
                "Time spent producing a message to Kafka.",
                registry=metrics_registry,
            ),
            websocket_connected=Gauge(
                "binance_websocket_connected",
                "Whether the Binance WebSocket is connected.",
                registry=metrics_registry,
            ),
            websocket_disconnects=Counter(
                "binance_websocket_disconnects_total",
                "Binance WebSocket disconnects.",
                registry=metrics_registry,
            ),
            websocket_reconnects=Counter(
                "binance_websocket_reconnects_total",
                "Binance WebSocket reconnects after an earlier connection.",
                registry=metrics_registry,
            ),
        )

    def connection_opened(self) -> None:
        if self._has_connected:
            self.websocket_reconnects.inc()
        self._has_connected = True
        self.websocket_connected.set(1)

    def connection_closed(self) -> None:
        self.websocket_disconnects.inc()
        self.websocket_connected.set(0)


producer_metrics = ProducerMetrics.create()


def on_open(ws) -> None:
    producer_metrics.connection_opened()


def on_close(ws, close_status_code, close_msg) -> None:
    producer_metrics.connection_closed()


def on_message(ws, message) -> None:
    producer_metrics.messages_received.inc()
    started_at = time.perf_counter()
    try:
        metadata = binance_producer.send(
            "binance-btcusdt-trade",
            value=message.encode("utf-8"),
        ).get(timeout=10)
        producer_metrics.messages_produced.inc()
        print(
            f"saved: topic={metadata.topic}, "
            f"partition={metadata.partition}, offset={metadata.offset}"
        )
    except Exception:
        producer_metrics.produce_errors.inc()
        logger.exception("Kafka did not save the Binance message")
    finally:
        producer_metrics.produce_latency.observe(
            time.perf_counter() - started_at
        )


def main() -> None:
    global binance_producer

    start_http_server(PROMETHEUS_PORT)
    producer_config = {
        "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS.split(","),
        "security_protocol": "SASL_PLAINTEXT",
        "sasl_mechanism": "SCRAM-SHA-512",
        "sasl_plain_username": KAFKA_USERNAME,
        "sasl_plain_password": KAFKA_PASSWORD,
        "client_id": "binance-btcusdt-streaming",
    }
    binance_producer = KafkaProducer(**producer_config)

    ws = websocket.WebSocketApp(
        BINANCE_WS,
        on_open=on_open,
        on_close=on_close,
        on_message=on_message,
    )
    ws.run_forever()


if __name__ == "__main__":
    main()

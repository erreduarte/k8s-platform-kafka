from dataclasses import dataclass

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
)


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

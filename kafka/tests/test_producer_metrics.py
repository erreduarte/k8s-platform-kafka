import importlib.util
import sys
import unittest
from pathlib import Path

from prometheus_client import CollectorRegistry

PRODUCER_PATH = (
    Path(__file__).parents[1]
    / "kafka_tools"
    / "producer"
    / "btcusdt@trade"
    / "producer.py"
)


def load_producer_module():
    spec = importlib.util.spec_from_file_location(
        "btcusdt_producer",
        PRODUCER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load producer module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PRODUCER = load_producer_module()


class ProducerMetricsTests(unittest.TestCase):
    def test_connection_lifecycle_metrics(self):
        metrics = PRODUCER.ProducerMetrics.create(CollectorRegistry())

        metrics.connection_opened()
        metrics.connection_closed()
        metrics.connection_opened()

        self.assertEqual(metrics.websocket_connected._value.get(), 1)
        self.assertEqual(metrics.websocket_disconnects._value.get(), 1)
        self.assertEqual(metrics.websocket_reconnects._value.get(), 1)

    def test_message_and_produce_counters(self):
        metrics = PRODUCER.ProducerMetrics.create(CollectorRegistry())

        metrics.messages_received.inc()
        metrics.messages_produced.inc()
        metrics.produce_errors.inc()
        metrics.produce_latency.observe(0.25)

        self.assertEqual(metrics.messages_received._value.get(), 1)
        self.assertEqual(metrics.messages_produced._value.get(), 1)
        self.assertEqual(metrics.produce_errors._value.get(), 1)
        self.assertEqual(metrics.produce_latency._sum.get(), 0.25)


if __name__ == "__main__":
    unittest.main()

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer as KafkaAvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext

SCHEMA_REGISTRY_URL = os.getenv(
    "SCHEMA_REGISTRY_URL",
    "http://127.0.0.1:8081",
)
TRADE_SCHEMA_PATH = Path(__file__).with_name("trade.avsc")
TRADE_FIELD_TYPES = {
    "e": str,
    "E": int,
    "s": str,
    "t": int,
    "p": str,
    "q": str,
    "T": int,
    "m": bool,
    "M": bool,
}


def to_trade_record(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("Binance trade message must be a JSON object")

    required_fields = tuple(TRADE_FIELD_TYPES)
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        raise ValueError(f"Binance trade message is missing fields: {missing_fields}")

    for field, expected_type in TRADE_FIELD_TYPES.items():
        value = payload[field]
        is_invalid_integer = expected_type is int and isinstance(value, bool)
        if is_invalid_integer or not isinstance(value, expected_type):
            raise TypeError(
                f"Binance trade field {field!r} must be a {expected_type.__name__}"
            )

    return {field: payload[field] for field in required_fields}


def create_avro_serializer(
    topic: str,
) -> Callable[[dict[str, Any]], bytes]:
    schema_registry = SchemaRegistryClient({"url": SCHEMA_REGISTRY_URL})
    avro_serializer = KafkaAvroSerializer(
        schema_registry,
        TRADE_SCHEMA_PATH.read_text(encoding="utf-8"),
    )

    def serialize(value: dict[str, Any]) -> bytes:
        record = to_trade_record(value)
        context = SerializationContext(topic, MessageField.VALUE)
        return avro_serializer(record, context)

    return serialize

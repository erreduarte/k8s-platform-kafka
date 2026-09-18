import os
import sys
from dataclasses import dataclass
from pathlib import Path

from pyflink.common import Configuration, Types, WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.file_system import (
    Encoder,
    FileSink,
    OutputFileConfig,
    RollingPolicy,
)
from pyflink.datastream.connectors.kafka import (
    KafkaOffsetsInitializer,
    KafkaSource,
)
from pyflink.datastream.functions import MapFunction

R2_DATA_BUCKET = "example-flink-data"
R2_CHECKPOINT_BUCKET = "example-flink-checkpoint"

# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Required environment variable is missing: {name}")
    return value


def positive_env(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"Environment variable must be positive: {name}")
    return value


# ---------------------------------------------------------------------------
# R2 configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class R2Settings:
    endpoint: str
    access_key_id: str
    secret_access_key: str
    prefix: str
    flush_interval_seconds: int

    @classmethod
    def from_environment(cls) -> "R2Settings":
        return cls(
            endpoint=required_env("R2_ENDPOINT"),
            access_key_id=required_env("R2_ACCESS_KEY_ID"),
            secret_access_key=required_env("R2_SECRET_ACCESS_KEY"),
            prefix=os.getenv("R2_PREFIX", "btcusdt"),
            flush_interval_seconds=positive_env(
                "R2_FLUSH_INTERVAL_SECONDS",
                60,
            ),
        )


def configure_r2_filesystem(
    env: StreamExecutionEnvironment,
    settings: R2Settings,
) -> None:
    configuration = Configuration()

    # Native Flink S3 filesystem (AWS SDK v2).
    configuration.set_string(
        "s3.access-key",
        settings.access_key_id,
    )
    configuration.set_string(
        "s3.secret-key",
        settings.secret_access_key,
    )

    configuration.set_string(
        "execution.checkpointing.storage",
        "filesystem",
    )
    configuration.set_string(
        "execution.checkpointing.dir",
        f"s3://{R2_CHECKPOINT_BUCKET}/flink-checkpoints",
    )

    env.configure(configuration)


def create_r2_sink(settings: R2Settings) -> FileSink:
    base_path = f"s3://{R2_DATA_BUCKET}/{settings.prefix}"
    interval_ms = settings.flush_interval_seconds * 1000

    return (
        FileSink.for_row_format(
            base_path,
            Encoder.simple_string_encoder(),
        )
        .with_rolling_policy(
            RollingPolicy.default_rolling_policy(
                rollover_interval=interval_ms,
                inactivity_interval=interval_ms,
            )
        )
        .with_output_file_config(
            OutputFileConfig.builder()
            .with_part_prefix("part")
            .with_part_suffix(".jsonl")
            .build()
        )
        .build()
    )


# ---------------------------------------------------------------------------
# Kafka
# ---------------------------------------------------------------------------

def kafka_jaas_config() -> str:
    username = required_env("KAFKA_USERNAME")
    password = required_env("KAFKA_PASSWORD")

    return (
        "org.apache.kafka.common.security.scram.ScramLoginModule required "
        f'username="{username}" password="{password}";'
    )


def create_kafka_source() -> KafkaSource:
    return (
        KafkaSource.builder()
        .set_bootstrap_servers(
            required_env("KAFKA_BOOTSTRAP_SERVERS")
        )
        .set_topics(
            required_env("KAFKA_BTCUSDT_TOPIC")
        )
        .set_group_id(
            "k8s-flink-btcusdt-consumer"
        )
        .set_starting_offsets(
            KafkaOffsetsInitializer.earliest()
        )
        .set_value_only_deserializer(
            SimpleStringSchema()
        )
        .set_property(
            "security.protocol",
            "SASL_PLAINTEXT",
        )
        .set_property(
            "sasl.mechanism",
            "SCRAM-SHA-512",
        )
        .set_property(
            "sasl.jaas.config",
            kafka_jaas_config(),
        )
        .build()
    )


class ConsoleLoggingMapFunction(MapFunction):
    def __init__(self) -> None:
        self.processed_count = 0

    def map(self, value: str) -> str:
        self.processed_count += 1
        print(
            f"[btcusdt-consumer] processing record #{self.processed_count}",
        )
        return value


def add_local_connector_jars(env: StreamExecutionEnvironment) -> None:
    jars_dir = Path(__file__).resolve().parents[2] / "jars"
    jars = tuple(
        path.as_uri() for path in jars_dir.glob("*.jar")
    )
    if jars:
        env.add_jars(*jars)


# ---------------------------------------------------------------------------
# Flink job
# ---------------------------------------------------------------------------

def run_job() -> None:
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10_000)
    env.set_python_executable(sys.executable)
    settings = R2Settings.from_environment()
    configure_r2_filesystem(env, settings)
    add_local_connector_jars(env)

    source = create_kafka_source()

    stream = env.from_source(
        source,
        WatermarkStrategy.no_watermarks(),
        "Binance BTCUSDT Source",
    )
    stream = stream.map(
        ConsoleLoggingMapFunction(),
        output_type=Types.STRING(),
    )

    stream.sink_to(create_r2_sink(settings))

    env.execute(
        "Binance BTCUSDT Consumer"
    )


if __name__ == "__main__":
    run_job()

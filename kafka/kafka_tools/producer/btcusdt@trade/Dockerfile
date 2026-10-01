FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "confluent-kafka[avro]>=2.8,<3.0" \
    "kafka-python==3.0.11" \
    "prometheus-client==0.23.1" \
    "websocket-client==1.9.0"

COPY kafka_tools/producer/btcusdt@trade/avro_serialization.py /app/avro_serialization.py
COPY kafka_tools/producer/btcusdt@trade/prometheus_metrics.py /app/prometheus_metrics.py
COPY kafka_tools/producer/btcusdt@trade/producer.py /app/producer.py
COPY kafka_tools/producer/btcusdt@trade/trade.avsc /app/trade.avsc

CMD ["python", "/app/producer.py"]

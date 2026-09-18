FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "kafka-python==3.0.11" \
    "prometheus-client==0.23.1" \
    "websocket-client==1.9.0"

COPY kafka_tools/producer/btcusdt@trade/producer.py /app/producer.py

CMD ["python", "/app/producer.py"]

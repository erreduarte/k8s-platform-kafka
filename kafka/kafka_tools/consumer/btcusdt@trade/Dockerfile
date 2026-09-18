FROM flink:2.3.0

USER root

# Python + pip
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Consumer dependencies. kafka-python and websocket-client belong to the local
# tools and are not required by the Flink consumer image.
ARG UV_VERSION=0.12.7
ARG PYTHON_VERSION=3.12.7
ARG APACHE_FLINK_VERSION=2.3.0
ARG FLINK_METRICS_PROMETHEUS_SHA1=03065b6c2396d42eb7ad8ef3c7745d1b1de25461
ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && /root/.local/bin/uv python install "${PYTHON_VERSION}" \
    && /root/.local/bin/uv venv --python "${PYTHON_VERSION}" /opt/venv \
    && /root/.local/bin/uv pip install --python /opt/venv/bin/python \
        "apache-flink==${APACHE_FLINK_VERSION}" \
    && chown -R flink:flink /opt/uv /opt/venv

# Prometheus metrics reporter
RUN curl -fsSL \
        "https://repo1.maven.org/maven2/org/apache/flink/flink-metrics-prometheus/${APACHE_FLINK_VERSION}/flink-metrics-prometheus-${APACHE_FLINK_VERSION}.jar" \
        -o "/opt/flink/lib/flink-metrics-prometheus-${APACHE_FLINK_VERSION}.jar" \
    && echo "${FLINK_METRICS_PROMETHEUS_SHA1}  /opt/flink/lib/flink-metrics-prometheus-${APACHE_FLINK_VERSION}.jar" \
        | sha1sum -c -

ENV FLINK_HOME=/opt/flink \
    FLINK_LIB_DIR=/opt/flink/lib \
    FLINK_PLUGINS_DIR=/opt/flink/plugins \
    FLINK_OPT_DIR=/opt/flink/opt \
    PATH="/opt/venv/bin:/opt/flink/bin:$PATH" \
    PYFLINK_CLIENT_EXECUTABLE=/opt/venv/bin/python

# Kafka connector
COPY kafka_tools/jars/flink-connector-kafka-5.0.0-2.2.jar /opt/flink/lib/
COPY kafka_tools/jars/kafka-clients-4.2.0.jar /opt/flink/lib/


# Native S3 filesystem plugin for the FileSink (Cloudflare R2 uses the S3 API).
RUN mkdir -p /opt/flink/plugins/s3-fs-native \
    && cp /opt/flink/opt/flink-s3-fs-native-*.jar \
        /opt/flink/plugins/s3-fs-native/

# R2 configuration for local Flink execution.
# Kubernetes deployments override this via FlinkDeployment.spec.flinkConfiguration.
RUN cat >> /opt/flink/conf/config.yaml <<'EOF'
# Cloudflare R2
s3.endpoint: https://object-storage.example.invalid
s3.path-style-access: true
s3.region: auto
EOF

# Job
COPY kafka_tools/consumer/btcusdt@trade/consumer.py /opt/flink/usrlib/consumer.py

USER flink

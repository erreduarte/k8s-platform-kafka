# Schema Registry

The `schema-registry` Argo CD Application deploys Confluent Schema Registry in
Kubernetes. Kafka remains external and runs on `kafka-1.example.invalid`, `kafka-2.example.invalid`,
and `kafka-3.example.invalid`.

## Ownership and prerequisites

- The chart owns only the Schema Registry Deployment and ClusterIP Service.
- Kafka owns the `_schemas` topic and remains managed by `ansible` in this monorepo.
- The Secret `schema-registry-kafka-credentials` is intentionally not stored in
  Git. The Ansible control-plane role creates it from `KAFKA_ADMIN_PASSWORD`
  before the Argo CD Application syncs.
- The Secret must contain the key `sasl-jaas-config` with a Kafka JAAS value for
  the existing `kafka-admin` SCRAM user.

For manual recovery only, create the Secret from a trusted administrative shell:

```bash
kubectl create namespace schema-registry --dry-run=client -o yaml | kubectl apply -f -
kubectl -n schema-registry create secret generic schema-registry-kafka-credentials \
  --from-literal='sasl-jaas-config=org.apache.kafka.common.security.scram.ScramLoginModule required username="kafka-admin" password="<KAFKA_ADMIN_PASSWORD>";' \
  --dry-run=client -o yaml | kubectl apply -f -
```

Do not commit the password or a generated Secret manifest.

## Kafka connection

The chart is configured for the current external Kafka contract:

```text
192.0.2.57:9092,192.0.2.58:9092,192.0.2.59:9092
security.protocol=SASL_PLAINTEXT
sasl.mechanism=SCRAM-SHA-512
topic=_schemas
topic replication factor=3
```

The Kafka brokers must be reachable from the Kubernetes node addresses on TCP
port `9092`. No PostgreSQL database, persistent volume, Kafka workload, or
Producer/Flink change is required.

## Verification

```bash
kubectl -n schema-registry rollout status deployment/schema-registry-schema-registry
kubectl -n schema-registry logs deployment/schema-registry-schema-registry --tail=200
kubectl -n schema-registry port-forward service/schema-registry-schema-registry 8081:8081
curl http://127.0.0.1:8081/subjects
```

An initial `[]` response from `/subjects` is valid. Describe `_schemas` with
the broker's existing `/etc/kafka/admin-client.properties` and confirm compact
cleanup policy and replication factor three.

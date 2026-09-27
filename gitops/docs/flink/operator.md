# Flink Operator

The Flink Kubernetes Operator is installed by the `flink-operator` Argo CD
Application in the `flink-operator` namespace. It watches the dedicated
`flink` namespace, where the BTCUSDT PyFlink consumer is declared as a
Git-managed `FlinkDeployment` and the BTCUSDT producer runs as a plain
Kubernetes `Deployment`.

The application currently tracks the operator `release-1.16.0-rc3` chart from
the Apache Flink Kubernetes Operator Git repository. This release is required
because the stable `1.15.0` CRD rejects `spec.flinkVersion: v2_3`. Keep the
operator release and the consumer image version aligned; migrate to a stable
`1.16.x` release supporting Flink 2.3 when it is published.

## Boundaries

- Kafka remains external to Kubernetes on the three broker VMs.
- `manifests/flink/btcusdt-consumer.yaml` deploys the BTCUSDT PyFlink consumer.
- The job image is published to `ghcr.io/erreduarte/k8s-platform-kafka-btcusdt-consumer`;
  promote immutable commit-SHA tags rather than relying on a moving tag.
- The GHCR package is private; pods use the externally managed
  `flink/ghcr-pull-secret` image pull Secret.
- Future PyFlink jobs will use a dedicated Kafka user, not `kafka-admin`.
- Flink checkpoints use the `example-flink-checkpoint` bucket under
  `flink-checkpoints/`.
- The `FlinkDeployment` sets `execution.checkpointing.dir` to that R2 path;
  this is required when `job.upgradeMode` is `last-state`.
- Processed data uses the `example-flink-data` bucket under the `R2_PREFIX` path.
- Cloudflare R2 credentials must be supplied through a Kubernetes Secret and
  must never be committed to Git.
- The consumer reads `username` and `password` from the
  `flink/kafka-flink-credentials` Secret; its broker list is declared in the
  FlinkDeployment. The producer additionally reads `bootstrapServers` from the
  same Secret.
- The producer image is published by `k8s-platform-kafka` as
  `ghcr.io/erreduarte/k8s-platform-kafka-btcusdt-producer:main` and uses the same Kafka
  credential keys. Its Deployment starts at zero replicas.
- Longhorn is not used for Flink state.
- The consumer uses Flink's checkpoint-aware `FileSink` with the native S3
  filesystem. Files become final after a successful checkpoint, and unfinished
  files are rolled back after a restart.
- The image exposes `/opt/flink` as the Flink runtime and loads the native S3
  plugin from `/opt/flink/plugins/s3-fs-native/`. The deployment starts the
  Python job through Flink's own `flink-python-2.3.0.jar`.
- The deployment requires `spec.flinkVersion: v2_3`; do not change it to
  `v2_2`, because the Flink 2.2 runtime does not support the consumer's
  Cloudflare R2 sink integration.
- The same R2 credential set is used with read/write access to both buckets.
- File names are controlled by Flink's sink task and rolling counter, not by
  Kafka offsets. Formal end-to-end exactly-once delivery is not claimed because
  R2 is external to Flink.
- The optional Flink admission webhook is disabled because cert-manager is not
  installed in the cluster. Enabling it requires deploying cert-manager first.

## Compatibility and dependency audit

The current compatibility tuple was verified across the GitOps and Kafka
repositories:

| Component | Version/source | Owner |
|---|---|---|
| Flink runtime image | `flink:2.3.0` | Kafka consumer Dockerfile |
| Flink CRD value | `v2_3` | This repository |
| PyFlink package | `apache-flink==2.3.0` | Kafka consumer Dockerfile |
| Python driver JAR | `flink-python-2.3.0.jar` | Flink runtime image |
| Kafka connector JAR | `flink-connector-kafka-5.0.0-2.2.jar` | Kafka consumer Dockerfile |
| Kafka client JAR | `kafka-clients-4.2.0.jar` | Kafka consumer Dockerfile |
| Operator chart | `release-1.16.0-rc3` | This repository |

Apache Maven Central currently publishes `flink-connector-kafka` through
`5.0.0-2.2`; no `2.3`-suffixed connector artifact is available. The existing
connector JAR is therefore retained as the latest published connector line,
while the Flink runtime, PyFlink package, driver JAR, and CRD remain on 2.3.
The GitOps `requirements-dev.txt` contains only repository validation tools;
it does not own Flink runtime dependencies and requires no change for this
compatibility update.

## Validation

After Argo CD syncs the application, verify the installation with read-only
commands:

```bash
kubectl -n argocd get application flink-operator
kubectl -n flink-operator get pods
kubectl get crd flinkdeployments.flink.apache.org
kubectl get crd flinksessionjobs.flink.apache.org
kubectl get namespace flink
kubectl -n flink get flinkdeployment btcusdt-consumer
kubectl -n flink get pods -l app=btcusdt-consumer
kubectl -n argocd get application btcusdt-producer
kubectl -n flink get deployment btcusdt-producer
```

The operator pod should be Ready and the Flink custom resource definitions
should exist before applying the job. The Kafka credentials Secret must exist
before the deployment can become Ready.

The Argo CD sync should not contain `cert-manager.io/v1` Issuer or Certificate
resources while the webhook remains disabled.

## BTCUSDT producer rollout

1. Confirm `flink/ghcr-pull-secret` exists and can pull from GHCR.
2. Confirm `flink/kafka-flink-credentials` contains `bootstrapServers`,
  `username`, and `password` without storing their values in Git.
3. Sync the `btcusdt-producer` Argo CD Application. It applies the raw
  manifest from `manifests/kafka/btcusdt-producer/` and intentionally leaves
  the Deployment at zero replicas.
4. Enable it only when required:

  ```bash
  kubectl -n flink scale deployment btcusdt-producer --replicas=1
  kubectl -n flink get pods -l app.kubernetes.io/name=btcusdt-producer
  ```

5. Disable it with `--replicas=0`. A future Argo CD sync restores the declared
  zero-replica state. The producer image currently uses the moving `main` tag;
  change the manifest to a reviewed immutable tag when promoting a release.

## BTCUSDT consumer rollout

1. Create `kafka-flink-credentials` in the `flink` namespace with the `username`
  and `password` keys. Keep the values outside Git.
2. Create `r2-flink-credentials` in the `flink` namespace with `endpoint`,
   `accessKeyId`, and `secretAccessKey`. Keep the values outside Git.
3. Create `ghcr-pull-secret` in the `flink` namespace as a Docker registry
  Secret for `ghcr.io`. Use a GitHub token with package read permission and
  keep the token outside Git. The Secret must contain the registry server,
  username, and token; do not commit or print its values.
4. Build and publish the consumer image, then update the FlinkDeployment to the
  exact published digest image. Do not use a moving tag such as `main` for a
  production promotion.
5. Sync the `flink-operator` Argo CD Application. Its operator source tracks
  the Apache `release-1.16.0-rc3` chart and its additional manifest source
  applies the namespace and the `FlinkDeployment`.
6. Verify the deployment and inspect the job manager logs:

  ```bash
  kubectl -n flink describe flinkdeployment btcusdt-consumer
  kubectl -n flink logs -l component: jobmanager
  ```

The job starts the Python file embedded at
`/opt/flink/usrlib/consumer.py`. It reads the external Kafka brokers at
`192.0.2.57:9092`, `192.0.2.58:9092`, and `192.0.2.59:9092`, consumes
`binance-btcusdt-trade`, and writes decoded records to R2 through Flink's
native S3 `FileSink`. The image is rebuilt and published by GitHub Actions; update the image tag deliberately when
promoting a new immutable image. Repository changes alone do not start or
restart the live job.

# k8s-platform-kafka Ansible

This destination tree manages only the Kubernetes cluster and Kafka broker VMs.
Other hosts and capabilities are intentionally outside this public mirror and
services. No unrelated roles or inventory entries are part of this destination.

## Managed hosts

```
Kafka:       kafka-1.example.invalid, kafka-2.example.invalid, kafka-3.example.invalid
Kubernetes:  control-plane-1.example.invalid, worker-1.example.invalid, worker-2.example.invalid
```

The baseline roles `common`, `users`, `shell`, and `firewall` run for every
managed host. Kafka uses `kafka_server`; Kubernetes uses `k8s_common`,
`k8s_control_plane`, and `k8s_worker`.

```bash
make setup
make lint
make check
make apply HOST=kafka_server
make apply HOST=k8s
```

Terraform owns VM hardware and disks. GitOps owns Kubernetes workloads after
bootstrap. This Ansible tree owns guest preparation and Kafka runtime
configuration only for the six listed hosts.

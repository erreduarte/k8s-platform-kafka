# Kafka server role

Prepares and runs the dedicated Kafka broker hosts in the `kafka_server`
inventory group.

## Topology and ownership

Kafka runs outside Kubernetes on three dedicated Proxmox VMs. Each VM combines
Kafka broker and KRaft controller roles:

| Host | IP | KRaft node ID |
|------|----|---------------|
| `kafka-1.example.invalid` | `192.0.2.57` | `1` |
| `kafka-2.example.invalid` | `192.0.2.58` | `2` |
| `kafka-3.example.invalid` | `192.0.2.59` | `3` |

Terraform owns VM hardware and the dedicated 30 GiB `scsi1` data-disk
attachment. This role owns the guest runtime. Kubernetes has no Kafka workload
integration; it hosts Kafka UI and scrapes broker metrics.

## Managed state

The role:

- installs Java 21 and Apache Kafka 4.3.1;
- creates the `kafka` system account;
- validates that `/dev/sdb` is an unpartitioned dedicated data disk of at least
  30 GiB;
- creates an `ext4` filesystem when needed and mounts it by UUID at
  `/var/lib/kafka`;
- requires at least 25 GiB free on the mounted data disk;
- creates the Kafka installation, configuration, and log directories;
- configures a combined broker/controller KRaft quorum;
- creates the `kafka-admin` SCRAM credential before enabling client authentication;
- formats each broker data directory once with the shared cluster ID;
- enables and starts the `kafka` systemd service;
- validates that the controller quorum elects a leader.
- exposes broker JVM metrics through Prometheus JMX exporter on TCP `9404`.

The role fails rather than formatting a partitioned, undersized, or unexpectedly
mounted disk.

## Firewall boundaries

The `firewall` role permits authenticated Kafka clients on `9092` from the LAN.
KRaft controller quorum traffic on `9093` and inter-broker traffic on `9094` are
restricted to the three broker IP addresses. JMX exporter metrics on `9404` are
restricted to the LAN addresses of the Kubernetes nodes because Cilium SNATs
Prometheus pod traffic before it reaches the brokers. No Kafka listener is
exposed publicly.

## KRaft configuration

The shared `kafka_cluster_id` is declarative and non-secret. It must never
change after a broker has been formatted. The role uses a combined
broker/controller KRaft topology and the following listeners:

- `SASL_PLAINTEXT` with SCRAM-SHA-512 on `9092` for clients;
- `PLAINTEXT` on `9094` for inter-broker replication;
- `CONTROLLER` on `9093` for the KRaft quorum.

## Access rules

Kafka uses ACLs. `kafka-admin` has full access. New users have no access until
an ACL grants it. `User:ANONYMOUS` is a Kafka super user only for the private
broker and controller listeners; UFW limits those listeners to the broker IPs.

The client listener on `9092` does not permit anonymous access. Use
`kafka-acls.sh` with the administrator client configuration to grant a user the
topic and consumer-group actions it needs.

The administrator password is read from the `KAFKA_ADMIN_PASSWORD` environment
variable and never stored in Git. It must contain at least 32 letters, digits,
periods, underscores, or hyphens. The role uses the static broker IP addresses
for quorum voters and advertised client listeners, so deployment does not depend
on DNS or `/etc/hosts` convergence.

SASL_PLAINTEXT authenticates clients but does not encrypt their traffic. It is
appropriate only for this isolated learning LAN. Add TLS before exposing Kafka
to an untrusted network.

## First deployment

Before the first deployment:

1. Confirm that each existing guest can resolve package repositories and that
  `apt update` succeeds. These VMs were created before the DNS correction in
  the Terraform template, so diagnose and correct guest DNS before running
  this role if either check fails.
2. Confirm that the Terraform-attached `scsi1` disk appears as `/dev/sdb` on
  each guest. The role can create a filesystem on this disk.
3. Confirm that the `ansible` bootstrap user and SSH host key are present.
4. Add a `KAFKA_ADMIN_PASSWORD` GitHub Actions secret for this repository. Generate
  a compatible value with `openssl rand -hex 24`.

Apply the initial configuration with both the Kafka and firewall tags so the
role's declared network boundaries are installed:

  make apply HOST=kafka_server TAGS=firewall,kafka_server

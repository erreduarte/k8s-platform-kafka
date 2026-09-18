# Longhorn

Longhorn is managed by the `longhorn` Argo CD Application in `applications/longhorn.yaml`. The root Application discovers it automatically. Longhorn installs the official Helm chart from `https://charts.longhorn.io/` into the `longhorn-system` namespace.

## Configuration

- Chart version: `1.12.1`, pinned for reproducible upgrades.
- Data engine: V1 only.
- Default replica count: 2, matching the two storage workers.
- Default data path: `/var/lib/longhorn`.
- Default storage class: `longhorn` is created but is **not** made the cluster default. Workloads must request `storageClassName: longhorn` explicitly.
- UI: remains `ClusterIP`; no ingress, Gateway, or monitoring integration is configured here.

## Storage nodes

The Ansible component owns the host requirements: the dedicated disks, `/var/lib/longhorn` filesystem mounts, `open-iscsi`, `nfs-common`, and `iscsid`.

Longhorn creates default disks only on Kubernetes nodes labelled `node.longhorn.io/create-default-disk=true`. Before merging this application, label only the dedicated storage workers from the controller:

```bash
kubectl label node worker-1.example.invalid node.longhorn.io/create-default-disk=true
kubectl label node worker-2.example.invalid node.longhorn.io/create-default-disk=true
```

Do not label `control-plane-1.example.invalid`: it has no dedicated Longhorn disk and must not store replicas.

## Verification

After Argo CD syncs the application:

```bash
kubectl -n longhorn-system get pods
kubectl -n longhorn-system get settings.longhorn.io default-data-path default-replica-count
kubectl -n longhorn-system get nodes.longhorn.io
kubectl get storageclass longhorn
```

The Longhorn nodes for `worker-1.example.invalid` and `worker-2.example.invalid` should show a schedulable disk at `/var/lib/longhorn`. The control plane should not have a Longhorn disk.

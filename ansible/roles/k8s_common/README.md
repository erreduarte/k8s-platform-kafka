# k8s_common

Prepares a Linux host to run as a Kubernetes node. This is the shared baseline applied to **every** machine in the cluster (control plane and workers) before any role-specific bootstrap runs.

The role does four things for every cluster node, in this order:

- Disables swap (Kubernetes assumes there is none).
- Loads and persists the kernel modules and sysctl entries that pod networking depends on.
- Installs containerd as the container runtime, configured to use the `systemd` cgroup driver so it matches kubelet.
- Installs `kubelet`, `kubeadm`, and `kubectl` from the official Kubernetes apt repository, then holds them so unattended upgrades cannot break the cluster.

On `longhorn_storage` workers only, it also prepares the host requirements for Longhorn V1. Longhorn itself is not installed by this role; Argo CD will install it from `k8s-platform-kafka`.

---

## Tasks structure

`tasks/main.yml` is a thin orchestrator that imports three task files in order:

| File | Responsibility |
|------|----------------|
| `system_prep.yml` | Disables swap (runtime + `/etc/fstab`), loads kernel modules `overlay` and `br_netfilter`, applies Kubernetes sysctls, and prepares Longhorn storage workers. |
| `install_containerd.yml` | Installs containerd, generates the default config, switches the cgroup driver to `systemd`, restarts the service when the config changes. |
| `install_kube_packages.yml` | Adds the Kubernetes apt repo and key, installs `kubelet` / `kubeadm` / `kubectl`, then marks them on hold. |

> `import_tasks` (not `include_tasks`) is used so role-level tags propagate into the child task files.

---

## Variables

Defined in `inventory/group_vars/k8s.yml`:

| Variable | Description |
|----------|-------------|
| `kubernetes_version` | Kubernetes minor series used in the apt repo URL (e.g. `v1.36`). Determines which kubelet/kubeadm/kubectl versions are available for install. |
| `longhorn_storage_device` | Dedicated disk expected on a `longhorn_storage` worker. Current value: `/dev/sdb`. |
| `longhorn_storage_path` | Mount point for the dedicated Longhorn disk. Current value: `/var/lib/longhorn`. |
| `longhorn_storage_filesystem` | Filesystem created on an empty dedicated disk. Current value: `ext4`. |
| `longhorn_storage_minimum_size_gib` | Minimum accepted disk size. Current value: 100 GiB. |
| `longhorn_storage_minimum_free_gib` | Minimum free space required after mounting. Current value: 45 GiB. |

---

## Operational notes

- **The apt cache must be refreshed after adding the Kubernetes repo.** Without it the install task fails with "Unable to locate package" on a brand-new host. The task sets `update_cache: true` for that reason.
- **Packages are held, not version-pinned.** Cluster upgrades go through `kubeadm`, not `apt upgrade`. To upgrade, first run: `apt-mark unhold kubelet kubeadm kubectl`.
- **Cgroup driver mismatch is a frequent boot failure.** kubelet defaults to the `systemd` cgroup driver, so containerd must be configured the same way. That is what the `SystemdCgroup = true` flip in `install_containerd.yml` exists for.
- **Longhorn preparation runs only on `longhorn_storage`.** It installs `open-iscsi` and `nfs-common`, enables `iscsid`, then validates and mounts the dedicated disk. It is selectable with `TAGS=longhorn_prerequisites`.
- **Disk safety comes first.** The disk must be partition-free, at least 100 GiB, and either empty or already `ext4`. It may only be mounted at `/var/lib/longhorn`; the role grows that filesystem after Terraform expands the disk and fails instead of formatting a different disk.

---

## Dependencies

- `ansible.posix`: sysctl module.
- `community.general`: modprobe and dpkg_selections modules.

# k8s_worker

Joins worker nodes to the Kubernetes cluster.

Applied only to hosts in the `k8s_worker` inventory group, after `k8s_common` has prepared the host and `k8s_control_plane` has produced a join command.

---

## How it works

The role is two tasks:

1. **Read the join command from the control plane.** Uses `ansible.builtin.slurp` with `delegate_to: "{{ groups['k8s_control_plane'][0] }}"` to pull `/root/join-command` from the first control-plane host. This avoids hardcoding a hostname.
2. **Run `kubeadm join`.** Skipped when `/etc/kubernetes/kubelet.conf` already exists, so re-runs are safe and existing workers are not re-joined.

---

## Adding a worker node

1. Add the host to `inventory/hosts.yml` under the `k8s_worker` group. Add it to `longhorn_storage` as well only when it has a dedicated Longhorn disk.
2. Create `inventory/host_vars/<hostname>.yml` with `ansible_host`.
3. Run `make bootstrap HOST=<hostname> USER=<initial-user>`.
4. Trigger the Deploy workflow, or locally:
   ```bash
   make apply HOST=<hostname> TAGS=bts_k8s_common,bts_k8s_worker,bts_k8s_cilium_status
   ```

---

## Dependencies

- `k8s_common` role must have run on this host first.
- `k8s_control_plane` must have run on the control-plane host (it writes `/root/join-command`).
- The `ansible` user on the control-plane host must be reachable by SSH from this node (covered by the standard SSH setup).
- A `longhorn_storage` worker must have its dedicated disk attached and verified before running `TAGS=longhorn_prerequisites`. This formats the configured disk and mounts it at `/var/lib/longhorn`; it does not install Longhorn.

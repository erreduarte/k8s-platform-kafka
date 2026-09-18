# k8s_control_plane

Bootstraps the Kubernetes control plane: initialises the cluster, installs Helm, deploys Cilium as the cluster network, installs Argo CD, and produces the join command workers will use.

Applied only to hosts in the `k8s_control_plane` inventory group. Currently a single-control-plane setup; multi-master HA is on the roadmap.

The role intentionally skips kube-proxy at `kubeadm init` because Cilium replaces it in eBPF. Hubble (network flow observability + UI) and Gateway API support are enabled from day one so they do not need to be retrofitted later.

---

## Tasks structure

`tasks/main.yml` imports the task files below in order. CoreDNS is configured and made Ready before Argo CD is installed because Argo CD needs cluster DNS to resolve its own services.

| File | Responsibility |
|------|----------------|
| `initialize_cluster.yml` | `kubeadm init` with `--skip-phases=addon/kube-proxy`. Writes the admin kubeconfig under `/root/.kube` and `/home/ansible/.kube`. |
| `install_helm.yml` | Installs Helm from the official binary release. Idempotent and architecture-aware (`amd64` / `arm64`). |
| `install_cosign.yml` | Installs cosign from the upstream GitHub release. Used to verify the Cilium chart signature. Idempotent and architecture-aware. |
| `install_cilium.yml` | Applies the Gateway API CRDs, verifies the Cilium chart signature with cosign, then installs Cilium directly from the OCI registry (`oci://quay.io/cilium/charts/cilium`) with kube-proxy replacement, Hubble (relay + UI), and Gateway API enabled. |
| `configure_coredns.yml` | Adds the missing CoreDNS permission to read EndpointSlices when needed and changes only the external DNS forwarding rule. It preserves the remaining Corefile configuration. |
| `wait_coredns.yml` | Waits for CoreDNS pods to become Ready before the role applies Argo CD. |
| `install_argocd.yml` | Creates the `argocd` namespace and applies the upstream Argo CD install bundle (`manifests/install.yaml`) with server-side apply. Pinned to `argocd_version`. |
| `generate_join.yml` | Mints a fresh `kubeadm` token (24 h TTL) and writes the join command to `/root/join-command`. |

Three task files are **not** imported by `main.yml` — they are invoked by dedicated plays in `site.yml` that run after workers have joined:

| File | Invoked by play | Purpose |
|------|----------------|---------|
| `wait_cilium.yml` | `Verify Cilium CNI readiness` | Gates the deploy on Cilium being fully Ready (see [Cilium readiness gate](#cilium-readiness-gate)). |
| `wait_argocd.yml` | `Verify Argo CD readiness` | Gates the deploy on Argo CD being fully Ready (see [Argo CD readiness gate](#argo-cd-readiness-gate)). |
| `configure_argocd.yml` | `Bootstrap Argo CD GitOps` | Registers the Git repository credential and applies the root Application (see [GitOps bootstrap](#gitops-bootstrap)). |

---

## Variables

Defined in `defaults/main.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `pod_network_cidr` | `10.244.0.0/16` | Passed to `kubeadm init` and to Cilium's IPAM as the cluster pod CIDR. |
| `helm_version` | `v3.16.2` | Helm binary release tag. |
| `cosign_version` | `v2.6.3` | cosign binary release tag. |
| `cilium_version` | `1.19.4` | Cilium Helm chart version. |
| `cilium_namespace` | `kube-system` | Namespace the Cilium release is installed into. |
| `coredns_namespace` | `kube-system` | Namespace containing the CoreDNS deployment and ConfigMap. |
| `coredns_upstream_dns` | `8.8.8.8`, `8.8.4.4` | External resolvers used for public DNS names. Explicit servers prevent CoreDNS from forwarding back to the cluster DNS Service through container `resolv.conf`. |
| `gateway_api_version` | `v1.2.0` | Gateway API release tag whose CRDs are applied before Cilium is installed. |
| `gateway_api_channel` | `experimental` | Gateway API CRD channel. `experimental` enables alpha resources (`TLSRoute`, `GRPCRoute`, etc.). Switch to `standard` to restrict to stable resources only. |
| `argocd_version` | `v3.2.0` | Argo CD release tag pulled from `https://raw.githubusercontent.com/argoproj/argo-cd/<argocd_version>/manifests/install.yaml`. Pinned per upstream recommendation. |
| `argocd_namespace` | `argocd` | Namespace the Argo CD bundle is applied into. |
| `argocd_gitops_repo_url` | `""` | SSH URL of the GitOps repository. Override in `inventory/group_vars/k8s.yml`. |
| `argocd_gitops_ssh_key` | `""` | SSH private key used by Argo CD to clone the repository. Must be set — read from the `ARGOCD_SSH_KEY` environment variable via `lookup('env', ...)`. An empty value triggers an assert failure. |
| `argocd_gitops_app_name` | `root` | Name of the root `Application` resource created in the `argocd` namespace. |
| `argocd_gitops_app_path` | `applications` | Path inside the GitOps repository that Argo CD watches for child Application manifests. |
| `argocd_gitops_target_revision` | `main` | Branch or tag Argo CD tracks in the GitOps repository. |

---

## Cilium installation values

The relevant Helm values set by `install_cilium.yml`:

| Value | Meaning |
|-------|---------|
| `ipam.mode=kubernetes` | Pods get IPs from the per-node CIDR allocated by `kube-controller-manager`, matching `--pod-network-cidr`. |
| `kubeProxyReplacement=true` | Cilium handles Service routing in eBPF instead of `kube-proxy`. Pairs with `--skip-phases=addon/kube-proxy` on `kubeadm init`. |
| `k8sServiceHost` / `k8sServicePort` | Direct apiserver address used by Cilium pods when `kube-proxy` is absent. Filled with the node's primary IPv4 and `6443`. |
| `hubble.enabled`, `hubble.relay.enabled`, `hubble.ui.enabled` | Flow observability and the web UI. |
| `gatewayAPI.enabled` | Cilium's Gateway API controller for ingress routing. |

> The Gateway API CRDs **must exist before** Cilium is installed with `gatewayAPI.enabled=true`, otherwise the Cilium operator will CrashLoop until they appear. The CRD apply step in `install_cilium.yml` runs first for that reason.

---

## CoreDNS configuration and readiness

The role configures CoreDNS after Cilium and before Argo CD. This order matters: CoreDNS needs Cilium service networking to contact the Kubernetes API, and Argo CD needs CoreDNS to resolve in-cluster services such as its Redis and repository server.

`configure_coredns.yml` checks whether the `coredns` service account can read individual EndpointSlices. If it cannot, the role applies a separate `ClusterRole` and `ClusterRoleBinding` that grant only `get` for `discovery.k8s.io/endpointslices`. This avoids editing the `system:coredns` role managed by kubeadm.

The task reads the live CoreDNS ConfigMap, replaces the default `forward .` target with `coredns_upstream_dns`, and applies the full Corefile only when that value changed. The rest of the Corefile remains unchanged. This avoids a DNS forwarding loop when the pod's `/etc/resolv.conf` points at cluster DNS.

When either correction changes the cluster, the role restarts CoreDNS immediately and waits for all pods with `k8s-app=kube-dns` to report `Ready`. The wait tries for about ten minutes. A CoreDNS pod that is only `Running` is not sufficient: its Kubernetes plugin can still be unavailable and prevent service-name lookups.

---

## Cilium readiness gate

A dedicated play in `site.yml` (`Verify Cilium CNI readiness`) runs **after** workers have joined and imports `wait_cilium.yml` from this role.

Why a separate play: `hubble-relay` and `hubble-ui` run as Deployments and only schedule once at least one schedulable worker exists (the control-plane node carries the `NoSchedule` taint). Running the wait inside `main.yml` would deadlock on a fresh cluster.

`wait_cilium.yml` runs three `kubectl wait --for=condition=Ready` calls in sequence:

| Pod label | Component |
|-----------|-----------|
| `k8s-app=cilium` | Cilium agent DaemonSet |
| `io.cilium/app=operator` | Cilium operator |
| `k8s-app=hubble-relay` | Hubble Relay |

Each attempt waits up to 30 s and is retried 20 times with 30 s between retries (~10 min total). Early attempts may return `rc=1` because the pods do not exist yet; this is expected and gets retried.

Triggered with the `bts_k8s_cilium_status` tag.

---

## Argo CD readiness gate

A dedicated play in `site.yml` (`Verify Argo CD readiness`) runs **after** workers have joined and imports `wait_argocd.yml` from this role.

Why a separate play, like Cilium: every Argo CD component (`argocd-server`, `argocd-repo-server`, `argocd-application-controller`, etc.) is a `Deployment` that does not tolerate the control-plane `NoSchedule` taint, so on a fresh cluster the pods stay `Pending` until at least one worker has joined. Running the wait inside `main.yml` would deadlock.

`wait_argocd.yml` runs three `kubectl wait --for=condition=Ready` calls in sequence:

| Pod label | Component |
|-----------|-----------|
| `app.kubernetes.io/name=argocd-server` | UI/API server |
| `app.kubernetes.io/name=argocd-repo-server` | Git repository server |
| `app.kubernetes.io/name=argocd-application-controller` | Application reconciler |

Each attempt waits up to 30 s and is retried 20 times with 30 s between retries (~10 min total). Early attempts may return `rc=1` because the pods do not exist yet; this is expected and gets retried.

Triggered with the `bts_k8s_argocd_status` tag.

---

## Argo CD

`install_argocd.yml` applies the upstream **non-HA** install bundle (`manifests/install.yaml`) into the `argocd` namespace using server-side apply. Server-side apply is required because the `ApplicationSet` CRD exceeds the 262 KB annotation limit imposed by client-side `kubectl apply`. `--force-conflicts` lets a re-run take ownership of fields that may already be tracked by another field manager (safe for fresh installs, required on upgrades).

Idempotency note: server-side apply prints `<kind>/<name> serverside-applied` for every resource on every run with no `unchanged` signal to filter on, so the apply task is marked `changed_when: false`. Re-runs reconcile drift without making spurious changes.

Network resilience: the manifest is fetched from `raw.githubusercontent.com` on every run, so the apply task retries up to 3 times with a 10 s delay to absorb brief DNS or HTTP hiccups.

The Argo CD pods are `Deployment`s that do not tolerate the control-plane `NoSchedule` taint. On a fresh cluster they will stay `Pending` until at least one schedulable worker has joined; this is expected and self-corrects once Play 7 (`Configure K8S Worker`) completes. The apply itself returns immediately, so it does not deadlock the play.

### Default TLS posture

The role does **not** provision a real certificate for `argocd-server`. On first start `argocd-server` generates a self-signed cert and persists it in the `argocd-secret` Secret. Until a real certificate is in place, clients must either trust the self-signed cert or pass `--insecure` on the `argocd` CLI.

Upgrade paths (not implemented here):

- **`argocd-server-tls` Secret** — create a `tls`-type Secret with `tls.crt` / `tls.key`; `argocd-server` picks up changes without restart. Pair with cert-manager for renewal. See [Argo CD TLS docs](https://argo-cd.readthedocs.io/en/stable/operator-manual/tls/).
- **Gateway API HTTPRoute** — expose `argocd-server` through the existing Cilium Gateway with TLS terminated at the Gateway listener; combine with `--insecure` on `argocd-server` (or keep upstream TLS and accept the self-signed cert for the in-cluster hop).

### Initial admin password

The initial `admin` password is auto-generated and stored in the `argocd-initial-admin-secret` Secret in the `argocd` namespace:

```
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d ; echo
```

Delete that Secret after rotating the password — it is re-created on demand if a reset is needed.

### Quick access

Until MetalLB and a Gateway/Ingress are installed, port-forward the API server manually:

```bash
kubectl -n argocd port-forward svc/argocd-server 8080:443 --address 0.0.0.0
# Then open https://<node-ip>:8080 in a browser (expect a self-signed cert warning)
```

The permanent solution — a `Gateway` + `HTTPRoute` backed by MetalLB — is tracked in the roadmap.

---

## GitOps bootstrap

`configure_argocd.yml` runs in a dedicated play (`Bootstrap Argo CD GitOps`, tag `bts_k8s_argocd_gitops`) **after** the Argo CD readiness gate. It:

1. Asserts `argocd_gitops_repo_url` and `argocd_gitops_ssh_key` are non-empty.
2. Applies a Kubernetes `Secret` labelled `argocd.argoproj.io/secret-type: repository` — the same credential you would add via the Argo CD UI under *Settings → Repositories*.
3. Applies the root `Application` pointing to the `applications/` path in the GitOps repository.

Both resources are applied with `kubectl apply -f -`, making the task idempotent.

The SSH private key (`argocd_gitops_ssh_key`) is read from the `ARGOCD_SSH_KEY` environment variable, which the GitHub Actions deploy workflow injects from a GitHub Secret. For local runs:

```bash
export ARGOCD_SSH_KEY="$(cat ~/.ssh/argocd-gitops)"
make apply TAGS=bts_k8s_argocd_gitops
```

---

## Re-running the pipeline (idempotency)

Safe to re-run against a cluster that is already configured. Each step is a no-op when its outcome is already in place:

- `kubeadm init` skipped when `/etc/kubernetes/admin.conf` exists.
- Helm install skipped when the installed version already matches `helm_version`.
- Gateway API CRD apply reports changed only when something actually changes.
- Cilium Helm release is declarative; no-op when the values already match.
- CoreDNS permission and DNS forwarding changes are no-ops when the service account already has access and the Corefile already uses `coredns_upstream_dns`. CoreDNS restarts only after a change.
- CoreDNS readiness is checked before Argo CD is installed.
- Argo CD install manifest is server-side applied; reconciles drift without spurious changes (always reports unchanged because the operation is `changed_when: false` — see Argo CD section above).
- `kubeadm join` skipped on workers when `/etc/kubernetes/kubelet.conf` exists.
- Join-command generation **always reports `changed`** because tokens rotate on every run (24 h TTL); this guarantees a valid token is always available for new workers.

Expected outcome on a stable cluster: only the join-command task reports a change.

---

## Adding a second control plane (HA)

**Not currently supported.** The role runs `kubeadm init`, which is only valid for the first control-plane node. A second control plane requires `kubeadm join --control-plane` with a certificate key generated during init (`--upload-certs`). Adding HA support requires a separate join flow and stacked-etcd bootstrap logic, tracked in the roadmap.

---

## Dependencies

- `kubernetes.core` collection (Helm modules).
- The `k8s_common` role must have run on the same host before this one.

---

## Roadmap

- [ ] **HA control plane**: second control-plane node via `kubeadm join --control-plane`, stacked etcd.
- [ ] **Expose Hubble UI via Gateway API**: replace `kubectl port-forward` with a `Gateway` + `HTTPRoute` on a hostname like `hubble.example.invalid`.
- [ ] **Expose Argo CD via Gateway API**: replace `kubectl port-forward` with a `Gateway` + `HTTPRoute` on a hostname like `argocd.example.invalid`. Combine with `--insecure` on `argocd-server` and terminate TLS at the Gateway.
- [ ] **Real TLS for `argocd-server`**: provision an `argocd-server-tls` Secret managed by cert-manager so browsers stop warning and the `argocd` CLI no longer needs `--insecure`.
- [ ] **Open Gateway API listener ports on K8s nodes**: introduce a `firewall_k8s_local_ports` (or similar) variable once the first `Gateway`/`HTTPRoute` starts listening on host ports.

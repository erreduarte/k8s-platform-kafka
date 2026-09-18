# kube-prometheus-stack

## Design

`applications/kube-prometheus-stack.yaml` installs the official
`prometheus-community/kube-prometheus-stack` chart version `88.5.2` in the
`monitoring` namespace. It provides the Prometheus Operator, Prometheus,
Alertmanager, kube-state-metrics, and an internal Grafana instance.

Prometheus retains 15 days of cluster metrics on a 20 GiB Longhorn PVC.
Alertmanager and Grafana also use Longhorn-backed PVCs. Their services remain
`ClusterIP`; external access is intentionally outside this Application's scope.

The Kubernetes control plane uses Cilium kube-proxy replacement, so the chart's
kube-proxy scrape is disabled. The Ansible component already runs `node_exporter` on each
Kubernetes VM host, so the chart's host-network node-exporter DaemonSet is also
disabled to avoid a port conflict. Host monitoring remains owned by Ansible;
this stack owns in-cluster monitoring.

Prometheus discovers `ServiceMonitor`, `PodMonitor`, and `PrometheusRule`
resources across namespaces without requiring Helm's release label. Add those
resources alongside workloads when they expose Prometheus metrics.

## Rollout and verification

1. Confirm the `longhorn` StorageClass is healthy.
2. Merge `applications/kube-prometheus-stack.yaml`; the root Application syncs
   the chart into `monitoring`.
3. Check the Application and stack pods:

   ```bash
   kubectl -n argocd get application kube-prometheus-stack
   kubectl -n monitoring get pods
   kubectl -n monitoring get pvc
   ```

4. Confirm Prometheus discovers its Kubernetes targets:

   ```bash
   kubectl -n monitoring port-forward service/kube-prometheus-stack-prometheus 9090:9090
   ```

   Open `http://localhost:9090/targets` and verify the expected built-in targets
   are up.

5. For the in-cluster Grafana instance, use a local port-forward:

   ```bash
   kubectl -n monitoring port-forward service/kube-prometheus-stack-grafana 3000:80
   ```

    The Grafana administrator credentials are supplied by the externally managed
    `monitoring/grafana-admin-credentials` Secret. Confirm that Secret exists;
    this repository does not generate or store the password.

## Operations

- Keep the chart version pinned and review the upstream upgrade notes before a
  major chart version change, especially because the stack owns cluster-wide
  CRDs.
- Do not delete its Prometheus Operator CRDs as part of a routine uninstall;
  first remove or migrate any `ServiceMonitor`, `PodMonitor`, or
  `PrometheusRule` resources that depend on them.
- The Ansible Prometheus/Grafana deployment on `controller.example.invalid` is separate and
  continues to monitor host-level exporters. It is not managed by this
  Application.

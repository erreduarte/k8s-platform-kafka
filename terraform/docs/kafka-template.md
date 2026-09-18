# Debian Kafka template

> Accurate as of 2026-08-26. This is a controlled build guide. It does not
> authorize a Terraform apply without a reviewed plan.

Terraform manages template VMID `997`, named `debian13-kafka.template`, after
it is added to remote state. Build it manually as a full clone of the Debian 13
template VMID `998`. Do not change the source template `998` with Terraform.

The template has a 20 GiB `scsi0` root disk, a Cloud-Init drive at `ide2` on
`local-lvm`, and a `serial0` socket console. Kafka is intentionally not
installed in the template. Broker VMs will add their independent 30 GiB Kafka
data disks at `scsi1`.

The template intentionally has no hostname, SSH user/key, DNS, or static IP.
Terraform sets these fixed per-VM values in the broker resources. This prevents
every clone from receiving the same network identity.

The Proxmox LAN is `192.0.2.0/26`, with gateway `192.0.2.1`. Future broker
resources must use unused addresses in this subnet with the `/26` prefix; they
must not use the former `/24` assumption.

## Prerequisite gate

Adding a Proxmox Cloud-Init drive does not install the guest software needed to
read it. Prepare VMID `997` in the Proxmox console. Do not use Terraform for
this creation step:

```text
qm clone 998 997 --full 1 --name debian13-kafka.template --storage local-lvm
qm set 997 --agent enabled=1 --scsihw virtio-scsi-single
qm set 997 --ide2 local-lvm:cloudinit
qm set 997 --boot order=scsi0\;ide2\;net0
qm start 997
```

Inside VMID `997`, verify both services:

```text
cloud-init --version
systemctl is-enabled cloud-init
systemctl is-enabled qemu-guest-agent
```

If `cloud-init` is missing or disabled, install and enable it with
`qemu-guest-agent` while VMID `997` has network access. Before making the VM a
reusable template, remove its instance-specific state:

```text
sudo cloud-init clean --logs --machine-id
sudo truncate -s 0 /etc/machine-id
sudo rm -f /var/lib/dbus/machine-id
sudo rm -f /etc/ssh/ssh_host_*
sudo rm -f /var/lib/systemd/network/*.lease
sudo poweroff
```

After the clean-up, convert VMID `997` to a Proxmox template:

```text
qm template 997
```

Create a temporary test VM from the template. Give it a static Cloud-Init
address and confirm that the guest uses it and the QEMU agent reports it to
Proxmox. Do not add the template to Terraform state until this passes. Generate
new SSH host keys on each broker's first boot; clones must never share keys.

## Completed readiness validation

VMID `997` was successfully created from VMID `998`, configured with Cloud-Init
and the QEMU guest agent, and converted to a Proxmox template. Disposable clone
VMID `996` validated the template with `192.0.2.60/26`, gateway
`192.0.2.1`, and DNS server `1.1.1.1`:

- Cloud-Init completed successfully.
- Gateway and DNS connectivity worked.
- `apt update` and `apt dist-upgrade` completed successfully.
- The `serial0` socket console was validated with `qm terminal 997`.

Terraform declares `serial_device { device = "socket" }` so its management of
VMID `997` preserves the validated Proxmox serial console.

For this template, Proxmox reports an unset machine type as one space, while the
provider reads it as `null`. Terraform ignores only `machine` so this formatting
difference does not trigger an in-place update. Terraform still manages every
other template setting, including `serial0`.

The initial test address `192.0.2.250/24` failed because it is outside the
actual `/26` LAN; do not reuse it.

## Terraform workflow

1. After completing the readiness gate, take the prescribed remote-state backup
   and review the Terraform import plan. It must adopt only VMID `997`; it must
   not alter VMIDs `141`, `151`, `152`, `998`, or `999`.
2. Apply only through the manual `apply_terraform_proxmox` workflow on `main`.
3. Confirm the resulting state protects VMID `997`, which is stopped, marked as
   a template, has `scsi0` at 20 GiB, `ide2` as a Cloud-Init disk on
   `local-lvm`, and `serial0` configured as a socket console.
4. Before defining brokers, create a temporary test VM. Confirm its hostname,
   static IPv4 address, SSH access, and guest-agent IPv4 report all come from
   Cloud-Init.
5. Remove the temporary VM only after confirming Terraform does not manage it.
   Never manually delete the protected template or Kafka brokers.

The Debian 13.5 netinst ISO at
`local:iso/debian-13.5.0-amd64-netinst.iso` is a fallback for rebuilding the
base image only if the VMID `997` clone cannot pass the Cloud-Init readiness
gate. It is not attached to, or required by, the normal VMID `997` clone
process.
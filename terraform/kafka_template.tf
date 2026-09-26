locals {
  debian_kafka_template_vm_id = 997
}

# VMID 998 is a manually maintained Debian 13 template. VMID 997 is prepared
# from a full clone of it before Terraform adopts and protects the result.
resource "proxmox_virtual_environment_vm" "debian_kafka_template" {
  name      = "debian13-kafka.template"
  node_name = local.proxmox_node_name
  vm_id     = local.debian_kafka_template_vm_id

  started             = false
  on_boot             = false
  reboot_after_update = true
  template            = true

  agent {
    enabled = true
  }

  cpu {
    cores   = 2
    sockets = 1
    type    = "x86-64-v2-AES"
  }

  memory {
    dedicated = 2048
  }

  scsi_hardware = "virtio-scsi-single"
  boot_order    = ["scsi0", "ide2", "net0"]

  # Preserve the serial console validated with `qm terminal 997`.
  serial_device {
    device = "socket"
  }

  # Preserve the 20 GiB root disk and its source-template performance settings.
  disk {
    cache        = "writeback"
    datastore_id = local.vm_datastore_id
    interface    = "scsi0"
    iothread     = true
    size         = 20
  }

  # The derived image must have cloud-init and qemu-guest-agent installed and
  # enabled before this resource is applied. See docs/kafka-template.md.
  initialization {
    datastore_id = local.vm_datastore_id
    interface    = local.cloud_init.interface
  }

  network_device {
    bridge = "vmbr0"
    model  = "virtio"
  }

  operating_system {
    type = "l26"
  }

  lifecycle {
    prevent_destroy = true
    # Proxmox reports its unset machine type as a single space. The provider
    # normalizes that value to null, so it must not cause a no-op update.
    ignore_changes = [machine]
  }
}

import {
  to = proxmox_virtual_environment_vm.debian_kafka_template
  id = "${local.proxmox_node_name}/${local.debian_kafka_template_vm_id}"
}
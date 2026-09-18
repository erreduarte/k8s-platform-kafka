resource "proxmox_virtual_environment_vm" "ubuntu_server_template" {
  name      = "ubuntu-server-template.example.invalid"
  node_name = local.proxmox_node_name
  vm_id     = local.ubuntu_server_template_vm_id

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
    dedicated = 3072
  }

  scsi_hardware = "virtio-scsi-single"
  boot_order    = ["scsi0", "ide2", "net0"]

  disk {
    datastore_id = local.vm_datastore_id
    interface    = "scsi0"
    iothread     = true
    size         = 50
  }

  initialization {
    datastore_id = local.vm_datastore_id
    interface    = local.cloud_init.interface

    ip_config {
      ipv4 {
        address = "192.0.2.101/24"
        gateway = local.cloud_init.ipv4_gateway
      }
    }
  }

  operating_system {
    type = "l26"
  }

  lifecycle {
    prevent_destroy = true
  }
}

import {
  to = proxmox_virtual_environment_vm.ubuntu_server_template
  id = "${local.proxmox_node_name}/${local.ubuntu_server_template_vm_id}"
}
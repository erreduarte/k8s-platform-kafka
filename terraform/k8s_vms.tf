locals {
  proxmox_node_name            = "hypervisor.example.invalid"
  vm_datastore_id              = "local-lvm"
  ubuntu_server_template_vm_id = 999
  cloud_init = {
    interface    = "ide2"
    ipv4_gateway = "192.0.2.1"
    username     = "ansible"
    public_keys = [
      "REPLACE_WITH_YOUR_PUBLIC_KEY",
    ]
  }

  k8s_vms = {
    cp01 = {
      vm_id         = 141
      name          = "control-plane-1.example.invalid"
      ipv4_address  = "192.0.2.41/26"
      mac_address   = "02:00:00:00:10:01"
      cores         = 2
      memory_mib    = 5120
      root_disk_gib = 50
      data_disk     = null
    }
    w01 = {
      vm_id         = 151
      name          = "worker-1.example.invalid"
      ipv4_address  = "192.0.2.51/26"
      mac_address   = "02:00:00:00:10:02"
      cores         = 4
      memory_mib    = 5120
      root_disk_gib = 70
      data_disk = {
        interface = "scsi1"
        size_gib  = 100
      }
    }
    w02 = {
      vm_id         = 152
      name          = "worker-2.example.invalid"
      ipv4_address  = "192.0.2.52/26"
      mac_address   = "02:00:00:00:10:03"
      cores         = 4
      memory_mib    = 5120
      root_disk_gib = 70
      data_disk = {
        interface = "scsi1"
        size_gib  = 100
      }
    }
  }
}

resource "proxmox_virtual_environment_vm" "k8s" {
  for_each = local.k8s_vms

  name      = each.value.name
  node_name = local.proxmox_node_name
  vm_id     = each.value.vm_id

  started             = true
  on_boot             = false
  reboot_after_update = true

  clone {
    full  = true
    vm_id = proxmox_virtual_environment_vm.ubuntu_server_template.vm_id
  }

  agent {
    enabled = true
  }

  cpu {
    cores   = each.value.cores
    sockets = 1
    type    = "x86-64-v2-AES"
  }

  memory {
    dedicated = each.value.memory_mib
  }

  scsi_hardware = "virtio-scsi-single"
  boot_order    = ["scsi0", "ide2", "net0"]

  disk {
    datastore_id = local.vm_datastore_id
    interface    = "scsi0"
    iothread     = true
    size         = each.value.root_disk_gib
  }

  dynamic "disk" {
    for_each = each.value.data_disk == null ? [] : [each.value.data_disk]

    content {
      backup       = true
      cache        = "none"
      datastore_id = local.vm_datastore_id
      discard      = "on"
      interface    = disk.value.interface
      iothread     = true
      size         = disk.value.size_gib
    }
  }

  network_device {
    bridge      = "vmbr0"
    mac_address = each.value.mac_address
    model       = "virtio"
  }

  operating_system {
    type = "l26"
  }

  initialization {
    datastore_id = local.vm_datastore_id
    interface    = local.cloud_init.interface

    ip_config {
      ipv4 {
        address = each.value.ipv4_address
        gateway = local.cloud_init.ipv4_gateway
      }
    }

    user_account {
      keys     = local.cloud_init.public_keys
      username = local.cloud_init.username
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [clone]
  }
}

import {
  for_each = local.k8s_vms

  to = proxmox_virtual_environment_vm.k8s[each.key]
  id = "${local.proxmox_node_name}/${each.value.vm_id}"
}

locals {
  kafka_vms = {
    kafka01 = {
      vm_id        = 157
      name         = "kafka-1.example.invalid"
      ipv4_address = "192.0.2.57/26"
      mac_address  = "02:00:00:00:00:57"
    }
    kafka02 = {
      vm_id        = 158
      name         = "kafka-2.example.invalid"
      ipv4_address = "192.0.2.58/26"
      mac_address  = "02:00:00:00:00:58"
    }
    kafka03 = {
      vm_id        = 159
      name         = "kafka-3.example.invalid"
      ipv4_address = "192.0.2.59/26"
      mac_address  = "02:00:00:00:00:59"
    }
  }
}

resource "proxmox_virtual_environment_vm" "kafka" {
  for_each = local.kafka_vms

  name      = each.value.name
  node_name = local.proxmox_node_name
  vm_id     = each.value.vm_id

  started             = true
  on_boot             = true
  reboot_after_update = true

  clone {
    datastore_id = local.vm_datastore_id
    full         = true
    vm_id        = proxmox_virtual_environment_vm.debian_kafka_template.vm_id
  }

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

  # A shared SCSI controller keeps guest device discovery aligned with the
  # Proxmox interface indexes: scsi0 is /dev/sda and scsi1 is /dev/sdb.
  scsi_hardware = "virtio-scsi-pci"
  boot_order    = ["scsi0", "ide2", "net0"]

  disk {
    cache        = "writeback"
    datastore_id = local.vm_datastore_id
    interface    = "scsi0"
    size         = 20
  }

  disk {
    backup       = true
    cache        = "none"
    datastore_id = local.vm_datastore_id
    discard      = "on"
    interface    = "scsi1"
    size         = 30
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

    dns {
      servers = ["1.1.1.1"]
    }

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

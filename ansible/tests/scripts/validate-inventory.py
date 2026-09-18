#!/usr/bin/env python3
"""Validate the Ansible inventory for structural correctness.

Checks performed (without connecting to any host):
  1. inventory/hosts.yml is valid YAML and parseable by Ansible.
  2. Every host has an ansible_host variable (IP address) defined in host_vars.
  3. Every IP in ansible_host is a valid IPv4 address.
  4. Every host belongs to at least one functional group beyond 'all'/'ungrouped'.
  5. hosts_entries in group_vars/all.yml covers every host's ansible_host IP.

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INVENTORY = REPO_ROOT / "inventory"
HOSTS_FILE = INVENTORY / "hosts.yml"

IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$"
)


def run_ansible_inventory() -> dict:
    """Run ansible-inventory --list and return the parsed JSON."""
    import json

    result = subprocess.run(
        ["ansible-inventory", "-i", str(HOSTS_FILE), "--list"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: ansible-inventory failed:\n{result.stderr.strip()}")
        sys.exit(1)

    return json.loads(result.stdout)


def get_all_hosts(inventory_data: dict) -> list:
    """Extract the list of all hostnames from inventory data."""
    meta = inventory_data.get("_meta", {})
    hostvars = meta.get("hostvars", {})
    return sorted(hostvars.keys())


def check_ansible_host(inventory_data: dict, hosts: list) -> list:
    """Check that every host has a valid ansible_host defined."""
    errors = []
    hostvars = inventory_data["_meta"]["hostvars"]

    for host in hosts:
        hvars = hostvars.get(host, {})
        ansible_host = hvars.get("ansible_host")

        if not ansible_host:
            errors.append(f"{host}: missing ansible_host (no IP defined in host_vars)")
            continue

        if not IPV4_RE.match(str(ansible_host)):
            errors.append(f"{host}: ansible_host '{ansible_host}' is not a valid IPv4 address")

    return errors


def check_group_membership(inventory_data: dict, hosts: list) -> list:
    """Check that every host belongs to at least one functional group."""
    errors = []
    skip_groups = {"all", "ungrouped"}

    host_groups = {h: set() for h in hosts}
    for group_name, group_data in inventory_data.items():
        if group_name.startswith("_") or group_name in skip_groups:
            continue
        if isinstance(group_data, dict):
            for member in group_data.get("hosts", []):
                if member in host_groups:
                    host_groups[member].add(group_name)

    for host in hosts:
        if not host_groups[host]:
            errors.append(f"{host}: not a member of any functional group")

    return errors


def check_hosts_entries_coverage(inventory_data: dict, hosts: list) -> list:
    """Check that hosts_entries in group_vars/all.yml covers every host IP."""
    import yaml

    errors = []
    hostvars = inventory_data["_meta"]["hostvars"]

    all_vars_path = INVENTORY / "group_vars" / "all.yml"
    if not all_vars_path.exists():
        errors.append("group_vars/all.yml not found — cannot check hosts_entries")
        return errors

    try:
        all_vars = yaml.safe_load(all_vars_path.read_text()) or {}
    except Exception as exc:
        errors.append(f"Failed to parse group_vars/all.yml: {exc}")
        return errors

    hosts_entries = all_vars.get("hosts_entries", [])
    covered_ips = {entry["ip"] for entry in hosts_entries if "ip" in entry}

    for host in hosts:
        ip = hostvars.get(host, {}).get("ansible_host")
        if ip and ip not in covered_ips:
            errors.append(
                f"{host}: ansible_host '{ip}' not found in hosts_entries (group_vars/all.yml)"
            )

    return errors


def main() -> int:
    if not HOSTS_FILE.exists():
        print(f"ERROR: Inventory file not found: {HOSTS_FILE}")
        return 1

    print("Validating inventory...")
    print(f"  Inventory: {HOSTS_FILE.relative_to(REPO_ROOT)}")

    inventory_data = run_ansible_inventory()
    hosts = get_all_hosts(inventory_data)

    if not hosts:
        print("ERROR: No hosts found in inventory")
        return 1

    print(f"  Hosts found: {', '.join(hosts)}")

    all_errors = []

    # Check ansible_host is defined and valid
    all_errors.extend(check_ansible_host(inventory_data, hosts))

    # Check group membership
    all_errors.extend(check_group_membership(inventory_data, hosts))

    # Check hosts_entries coverage
    all_errors.extend(check_hosts_entries_coverage(inventory_data, hosts))

    if all_errors:
        print(f"\nFAILED — {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"\nPASSED — {len(hosts)} host(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

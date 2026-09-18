#!/usr/bin/env bash
# Scan SSH fingerprints for any inventory host not yet in known_hosts.
#
# Reads ansible_host IPs from the inventory and runs ssh-keyscan for each
# one not already present in ~/.ssh/known_hosts. Safe to run repeatedly.
#
# Works as any user on any machine with the repo cloned:
#   - On a controller node: updates that node's known_hosts
#   - On a development machine: updates the local known_hosts

set -euo pipefail

INVENTORY="${1:-inventory/hosts.yml}"
KNOWN_HOSTS="${HOME}/.ssh/known_hosts"

if ! command -v ansible-inventory > /dev/null 2>&1; then
  echo "ansible-inventory not found — run 'make setup' to install ansible-core and required collections" >&2
  exit 1
fi

touch "${KNOWN_HOSTS}"
chmod 600 "${KNOWN_HOSTS}"

mapfile -t IPS < <(
  ansible-inventory -i "${INVENTORY}" --list 2>/dev/null \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
hostvars = data.get('_meta', {}).get('hostvars', {})
for vars in hostvars.values():
    ip = vars.get('ansible_host')
    if ip:
        print(ip)
"
)

if [[ ${#IPS[@]} -eq 0 ]]; then
  echo "No hosts with ansible_host found in inventory"
  exit 0
fi

updated=0
for ip in "${IPS[@]}"; do
  echo "  scanning:      ${ip}"
  new_key=$(ssh-keyscan -H "${ip}" 2>/dev/null) || true
  if [[ -z "${new_key}" ]]; then
    echo "  unreachable:   ${ip} (skipped)"
    continue
  fi
  # Remove stale entry (handles key changes after VM recreation) then add fresh key
  ssh-keygen -R "${ip}" -f "${KNOWN_HOSTS}" > /dev/null 2>&1 || true
  echo "${new_key}" >> "${KNOWN_HOSTS}"
  updated=$((updated + 1))
done

echo ""
echo "${updated} host(s) updated in ${KNOWN_HOSTS}"

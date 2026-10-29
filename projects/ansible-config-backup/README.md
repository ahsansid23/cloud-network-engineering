# Network configuration backup (Ansible)

A lab playbook that reads a Cisco IOS running configuration over Ansible's network CLI connection and writes a local backup file. The inventory uses documentation-only address `192.0.2.10`; it is a placeholder, not a reachable device.

## Design

1. The `network_devices` inventory group selects target lab routers.
2. `cisco.ios.ios_command` runs `show running-config`.
3. The returned configuration is written on the controller using `delegate_to: localhost`.
4. File mode `0600` limits local access on POSIX systems.

The playbook currently writes one file per inventory host into the project directory. Operational use needs a dedicated protected backup directory, retention strategy, integrity checks, encryption, and a restore-test procedure.

## Prerequisites

- Ansible Core with `ansible.netcommon` and `cisco.ios` collections installed.
- A disposable Cisco IOS/IOS XE lab device reachable through a supported management network.
- Credentials supplied securely through Ansible Vault, an approved credential plugin, or a secret manager.
- SSH host-key verification and the lab's access policy configured before execution.

## Safe preparation

1. Replace the placeholder host address only with a lab device you are authorized to administer.
2. Replace the inventory username placeholder and provide passwords/enable secrets via Vault or a secret manager—not plaintext inventory or source control.
3. Run syntax and inventory checks:

```bash
ansible-playbook --syntax-check backup.yml
ansible-inventory -i inventory.ini --graph
```

4. Confirm the target group and intended controller-side destination.
5. Run only against the lab after adapting credential variables and the playbook:

```bash
ansible-playbook -i inventory.ini backup.yml --ask-vault-pass
```

The example does not define a Vault variable schema, so adapt it before using `--ask-vault-pass`. Syntax validation does not prove collections, device authentication, privilege mode, or command output work on your device.

## Operational safeguards

- A running configuration may contain usernames, SNMP communities, keys, management addresses, banners, and topology. Treat backups as sensitive even for a lab.
- Store backups outside a public repository; restrict filesystem permissions, encrypt at rest and in transit, define retention, and audit access.
- Consider timestamped snapshots, checksums, diffs, failure handling, and an explicit restore drill.
- Test host-key validation; do not disable it merely to make a lab connect.
- Never use this playbook as an unattended production change mechanism.

## Validation and limitations

Offline syntax/inventory checks can be performed when Ansible and the required collections are installed. No live device session, successful backup, or restore test is claimed here. The example supports Cisco IOS through `cisco.ios`; other platforms require their own supported collections and commands.

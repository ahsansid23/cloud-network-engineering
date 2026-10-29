# IPAM auditor operations runbook

## Purpose and boundaries

Use this runbook when validating an address-plan export before a network change. The auditor is read-only and offline. It does not validate reachability, routing policy, cloud-provider quotas, or business intent.

## Pre-flight checklist

- [ ] Confirm the export came from the approved system of record and is current.
- [ ] Confirm the export is authorized for local processing.
- [ ] Remove credentials, customer names, and unrelated sensitive columns.
- [ ] Confirm the CSV has `network_name,site,vrf,cidr` columns.
- [ ] Confirm site and VRF labels are normalized and meaningful.
- [ ] Decide whether the input contains only allocatable prefixes or also aggregates/pools.
- [ ] Use a protected workspace for real internal address data; never commit that data.

## Run the audit

From this directory:

```bash
python audit.py inventory.csv
python audit.py inventory.csv --format json
python -m unittest -v
```

The sample file is deliberately unhealthy. Exit code 1 is expected for findings. For automation, capture stdout and exit status separately; exit code 2 indicates a file/header problem that should be fixed before interpreting results.

## Triage decision guide

### Duplicate network

1. Compare both rows' owner, purpose, site, and VRF in the authoritative source.
2. Determine whether this is a duplicate record, intentional shared address space, or a real double allocation.
3. Check connectivity relationships such as VPN, VPC/VNet peering, transit routing, and route leaking.
4. Correct the source of truth or document an approved exception; do not delete records merely to make the report green.

### Contained network

1. Determine whether the larger prefix is a summary, delegated pool, or actual allocation.
2. Confirm that the smaller prefix belongs to the larger pool and that this is allowed by the inventory model.
3. Check routing advertisements and allocation ownership separately; this tool cannot tell whether the parent is advertised.
4. If the relationship is intentional, keep the data model explicit and record the rationale. Consider a future type-aware policy rather than ignoring every containment result.

### Invalid CIDR or missing field

1. Verify the intended prefix with the source owner.
2. Do not automatically normalize host bits without approval; a typo may indicate the wrong subnet.
3. Re-export or correct the source record, then rerun the audit.

## Change evidence to retain

For a controlled change, retain according to internal policy:

- sanitized inventory version or source revision;
- tool version/commit and run timestamp;
- text report or JSON artifact;
- finding disposition and reviewer;
- change ticket, implementation plan, validation plan, and rollback reference.

Avoid placing sensitive inventory or raw reports in a public repository or public CI logs.

## Acceptance criteria

A reviewer should be able to explain every finding. A clean exit code is useful but not sufficient: validate cloud subnet constraints, routing reachability, NAT, VPN/peering interactions, reserved ranges, and dependent services as relevant to the actual change.

## Recovery and rollback

The tool makes no network changes, so there is nothing to roll back from running it. If a subsequent implementation changes address allocations, follow the approved change plan and rollback procedure for that implementation. Never use this utility as automatic authorization to renumber or deploy.

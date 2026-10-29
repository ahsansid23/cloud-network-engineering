# IPAM Overlap Auditor

An offline, dependency-free Python utility that validates a CSV IP address management (IPAM) inventory and identifies duplicate or overlapping IPv4/IPv6 allocations. It is intended as a pre-change quality gate for address plans, lab inventories, and sanitized exports from an authoritative IPAM source.

**Read-only by design.** The tool does not contact routers, cloud APIs, DNS, or external services, and never edits the input inventory.

## Why this matters

Address-plan errors can surface later as failed VPC peering, ambiguous routing, unexpected reachability, VPN conflicts, or difficult incident diagnosis. The auditor makes common allocation inconsistencies visible before a change is proposed. It complements the portfolio's BGP peer audit (routing state) and network health report (availability metrics); it replaces neither.

## Capabilities

- Validates required CSV fields and IPv4/IPv6 CIDR syntax.
- Requires canonical network prefixes: `10.20.1.5/24` is rejected rather than silently normalized to `10.20.1.0/24`.
- Reports identical prefixes as `DUPLICATE_NETWORK`.
- Reports nested prefixes as `CONTAINED_NETWORK`.
- Compares only records with the same exact `site` and `vrf` values.
- Supports human-readable text and machine-consumable JSON output.
- Uses only Python's standard library: `argparse`, `csv`, `ipaddress`, and `json`.

## Architecture

```text
CSV inventory
    |
    v
Header + required-field validation
    |
    v
Strict IPv4/IPv6 CIDR parsing
    |
    v
Valid records grouped logically by (site, VRF)
    |
    v
Pairwise overlap comparison
    |
    v
Text or JSON findings + process exit code
```

The parser preserves source row numbers. Invalid rows become findings and are excluded from overlap comparisons because their network objects cannot be trusted. Valid records are compared pairwise; this is simple and auditable, with O(n²) comparisons in the worst case. For very large inventories, a sorted interval/prefix index would be a sensible next design step.

## Prerequisites

- Python 3.9+ recommended.
- No pip install, cloud account, credentials, or network access.
- Run from this directory or pass an explicit path to the CSV.

## Quick start

```bash
python audit.py inventory.csv
python audit.py inventory.csv --format json
python -m unittest -v
```

The supplied inventory intentionally contains two overlap findings: an IPv4 summary/child pair and an IPv6 prefix/child pair. Therefore the sample audit is expected to return exit code **1**. This is a deliberately unhealthy fixture, not a tool failure.

To confirm a clean pass, create a separate temporary CSV with disjoint prefixes in each scope and run the same command. Do not remove findings from the sample unless intentionally changing the teaching example.

## CSV schema

Required columns:

| Column | Meaning | Example |
|---|---|---|
| `network_name` | Human-readable allocation identifier | `app-subnet-a` |
| `site` | Site, region, or administrative location | `dc1` |
| `vrf` | Routing/tenant scope label | `default` |
| `cidr` | Canonical network prefix | `10.40.8.0/24` |

An optional `purpose` column is accepted and ignored. Additional columns are also ignored. Header names and site/VRF values are exact and case-sensitive; normalize exports before auditing if your source uses inconsistent naming.

Use documentation-only prefixes in public examples (for example, IPv4 TEST-NET ranges and IPv6 `2001:db8::/32`). Do not publish real customer or internal network inventories.

## Understanding findings

| Code | Meaning | First response |
|---|---|---|
| `MISSING_FIELD` | A row lacks a required value | Correct the source row; do not infer a scope |
| `INVALID_CIDR` | Prefix is invalid or has host bits set | Confirm intended network boundary and canonicalize at source |
| `DUPLICATE_NETWORK` | Two allocations use the same prefix in the same site/VRF | Verify ownership and whether records represent one allocation twice |
| `CONTAINED_NETWORK` | One valid prefix is wholly inside another in the same site/VRF | Determine whether one is a summary, parent pool, or conflicting allocation |

A parent aggregate and child subnet are not automatically a fault in every data model. This tool intentionally treats any same-scope overlap as a finding because it cannot infer allocation intent. If your inventory mixes routed summaries, pools, and allocatable subnets, partition those classes before treating the report as a gate.

## Exit codes and automation

- `0`: no findings.
- `1`: one or more inventory findings; review the report.
- `2`: input file could not be read or the CSV header is invalid.

A CI pipeline can use exit code 1 to block an address-plan change, but first decide whether all overlaps are prohibited by your inventory model. Capture JSON output as an artifact if structured review is needed. Never automatically apply network changes based on this report.

## Validation

```bash
python -m unittest -v
python audit.py inventory.csv
python audit.py inventory.csv --format json
```

Tests cover clean allocations, containment, duplicate prefixes, site/VRF scope separation, IPv4/IPv6 handling, non-canonical CIDRs, missing fields, invalid headers, and CLI output/exit status. The sample contains expected findings, so shell wrappers should account for exit code 1 rather than treating every non-zero result as a runtime exception.

## Safe operational workflow

1. Export a least-privilege, read-only inventory from the system of record.
2. Remove credentials, customer identifiers, and sensitive metadata; retain only fields needed for the check.
3. Normalize site and VRF naming using a documented convention.
4. Run the auditor and retain timestamp, source revision, and report alongside the proposed change.
5. Investigate each finding against intended address ownership, route summaries, NAT, peering, and tenant boundaries.
6. Have the network owner approve any allocation change; plan rollback and check dependent systems.
7. Re-run against the revised inventory before implementation.

See [engineering notes](docs/engineering-notes.md) for networking concepts and [the operations runbook](docs/operations-runbook.md) for triage steps.

## Limitations and non-goals

- Site and VRF scope matching is exact and case-sensitive; route leaking between VRFs is not modeled.
- NAT, policy-based routing, overlapping tenant address spaces, DHCP reservations, cloud-specific reserved addresses, IPv6 zone IDs, and provider-specific subnet constraints are not modeled.
- A containment finding may be intentional for hierarchical IPAM or route aggregation. Human review is required.
- The pairwise algorithm is O(n²) and may not suit millions of rows.
- CSV is an interchange format, not an authoritative IPAM system; there is no API integration, persistence, authentication, or change execution.
- Tests use synthetic data only. They do not prove behavior against a live router, cloud account, or vendor IPAM export.

## Further reading

- Python `ipaddress` documentation: https://docs.python.org/3/library/ipaddress.html
- Validate network design against your organization's IPAM, routing, and cloud-provider standards.

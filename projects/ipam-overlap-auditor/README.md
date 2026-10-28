# IPAM Overlap Auditor

An offline Python tool that validates a CSV IP address management (IPAM) inventory and reports overlapping IPv4/IPv6 allocations within the same site and VRF. It complements the portfolio's BGP session and network health checks by checking address-plan consistency rather than live reachability or routing state.

## What it checks

- Invalid or non-canonical CIDRs (for example, 10.0.0.5/24 instead of 10.0.0.0/24).
- Duplicate allocations with the same prefix.
- One allocation contained within another.
- Scope boundaries: identical prefixes in different sites or VRFs are not compared.

## Design

audit.py uses only the Python standard library (csv, ipaddress, and argparse). It parses the inventory, validates rows, compares valid network pairs sharing the same (site, vrf) scope, and emits a human-readable or JSON report. It never connects to routers, cloud APIs, or external services and never changes the inventory.

## Prerequisites

- Python 3.9 or later recommended.
- No third-party packages.

## Run safely

From this directory:

    python audit.py inventory.csv
    python audit.py inventory.csv --format json
    python -m unittest -v

Exit codes: 0 means no findings, 1 means one or more inventory findings, and 2 means the input file could not be read or its CSV header is invalid. The sample inventory intentionally contains two containment findings, so the first command is expected to exit with code 1.

## CSV schema

Required columns: network_name,site,vrf,cidr. An optional purpose column is ignored by the auditor. CIDRs must be canonical network prefixes; host bits set in a CIDR are reported as invalid instead of silently normalised.

## Validation

The unit suite covers clean allocations, containment, duplicate prefixes, site/VRF scoping, IPv4/IPv6 handling, malformed CIDRs, missing fields, CSV headers, and CLI behavior. Run the suite locally before adapting it to operational inventory data.

## Limitations

- The tool treats every overlap in the same site/VRF as a finding. If your source inventory intentionally mixes route summaries with child allocations, filter summaries out or maintain a separate inventory for actual address allocations; do not simply suppress findings without review.
- Site and VRF matching is exact and case-sensitive. Normalise naming conventions before audit.
- It does not model VRF route leaking, NAT, policy-based routing, shared address spaces across tenants, DHCP reservations, or cloud-provider-specific allocation rules.
- It is a CSV validation utility, not a replacement for an authoritative IPAM system. Review findings before making address-plan changes.
- Sample networks are synthetic/documentation-only. No production inventory or live network validation is included.

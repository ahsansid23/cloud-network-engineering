#!/usr/bin/env python3
"""Offline CSV IPAM overlap auditor; uses only the Python standard library."""

import argparse
import csv
import ipaddress
import json
import sys
from itertools import combinations
from pathlib import Path

REQUIRED_COLUMNS = {"network_name", "site", "vrf", "cidr"}


def load_inventory(path):
    """Load CSV rows and reject files that lack the required column headers."""
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV is empty or has no header row")
        missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
        if missing:
            raise ValueError("CSV is missing required columns: " + ", ".join(missing))
        return list(reader)


def audit_rows(rows):
    """Return findings for malformed rows and overlapping networks in one site/VRF."""
    entries = []
    findings = []

    for row_number, row in enumerate(rows, start=2):
        values = {key: (row.get(key) or "").strip()
                  for key in ("network_name", "site", "vrf", "cidr")}
        missing = [key for key, value in values.items() if not value]
        if missing:
            findings.append({
                "severity": "ERROR", "code": "MISSING_FIELD", "row": row_number,
                "network_name": values["network_name"] or None,
                "cidr": values["cidr"] or None,
                "message": "Missing required value(s): " + ", ".join(missing),
            })
            continue

        try:
            network = ipaddress.ip_network(values["cidr"], strict=True)
        except ValueError as exc:
            findings.append({
                "severity": "ERROR", "code": "INVALID_CIDR", "row": row_number,
                "network_name": values["network_name"], "cidr": values["cidr"],
                "message": f"Invalid or non-canonical CIDR: {exc}",
            })
            continue

        entries.append({
            "row": row_number, "network_name": values["network_name"],
            "site": values["site"], "vrf": values["vrf"],
            "cidr": network.with_prefixlen, "network": network,
        })

    for first, second in combinations(entries, 2):
        if first["site"] != second["site"] or first["vrf"] != second["vrf"]:
            continue
        net_a, net_b = first["network"], second["network"]
        if not net_a.overlaps(net_b):
            continue

        if net_a == net_b:
            code, description = "DUPLICATE_NETWORK", "identical network allocations"
        else:
            # Canonical CIDR blocks that overlap are necessarily nested.
            code, description = "CONTAINED_NETWORK", "one network contains the other"

        findings.append({
            "severity": "ERROR", "code": code,
            "row_a": first["row"], "row_b": second["row"],
            "network_a": {"name": first["network_name"], "cidr": first["cidr"]},
            "network_b": {"name": second["network_name"], "cidr": second["cidr"]},
            "scope": {"site": first["site"], "vrf": first["vrf"]},
            "message": f"{description} in site={first['site']!r}, vrf={first['vrf']!r}",
        })

    return sorted(findings, key=lambda item: (
        item.get("row_a", item.get("row", 0)), item.get("row_b", 0), item["code"]))


def render_text(findings):
    if not findings:
        return "PASS: no invalid rows or overlapping networks found."
    lines = [f"FAIL: {len(findings)} finding(s) detected."]
    for finding in findings:
        if "network_a" in finding:
            a, b = finding["network_a"], finding["network_b"]
            lines.append(
                f"- {finding['code']}: {a['name']} ({a['cidr']}) [row {finding['row_a']}] vs "
                f"{b['name']} ({b['cidr']}) [row {finding['row_b']}]; "
                f"site={finding['scope']['site']}, vrf={finding['scope']['vrf']}"
            )
        else:
            lines.append(
                f"- {finding['code']}: row {finding['row']} "
                f"({finding.get('network_name') or 'unnamed'}, "
                f"{finding.get('cidr') or 'no CIDR'}): {finding['message']}"
            )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find invalid CIDRs and overlapping IPAM allocations in a CSV inventory.")
    parser.add_argument("inventory", help="CSV file with network_name,site,vrf,cidr columns")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="output format (default: text)")
    args = parser.parse_args(argv)

    try:
        findings = audit_rows(load_inventory(args.inventory))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"finding_count": len(findings), "findings": findings}, indent=2))
    else:
        print(render_text(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

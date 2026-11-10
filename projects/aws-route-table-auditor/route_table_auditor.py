#!/usr/bin/env python3
"""Offline auditor for AWS EC2 DescribeRouteTables JSON exports."""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TARGET_FIELDS = (
    "CarrierGatewayId",
    "CoreNetworkArn",
    "EgressOnlyInternetGatewayId",
    "GatewayId",
    "InstanceId",
    "LocalGatewayId",
    "NatGatewayId",
    "NetworkInterfaceId",
    "OdbNetworkArn",
    "TransitGatewayId",
    "VpcEndpointId",
    "VpcPeeringConnectionId",
)
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _required_string(value: Any, field: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: {field} must be a non-empty string")
    return value.strip()


def _route_destination(route: dict[str, Any], context: str) -> tuple[str, bool]:
    """Return a canonical destination and whether it is a default route."""
    fields = (
        "DestinationCidrBlock",
        "DestinationIpv6CidrBlock",
        "DestinationPrefixListId",
    )
    present = [(field, route[field]) for field in fields if route.get(field) not in (None, "")]
    if len(present) != 1:
        raise ValueError(
            f"{context}: expected exactly one destination field, found {len(present)}"
        )

    field, raw_value = present[0]
    value = _required_string(raw_value, field, context)
    if field == "DestinationPrefixListId":
        return f"prefix-list:{value}", False

    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise ValueError(f"{context}: invalid CIDR {value!r}") from exc
    return str(network), network.prefixlen == 0


def _targets(route: dict[str, Any]) -> dict[str, str]:
    return {
        field: str(route[field])
        for field in TARGET_FIELDS
        if route.get(field) not in (None, "")
    }


def analyse(document: Any) -> dict[str, Any]:
    """Analyse a DescribeRouteTables response without contacting AWS."""
    if not isinstance(document, dict):
        raise ValueError("input must be a JSON object")

    tables = document.get("RouteTables")
    if not isinstance(tables, list):
        raise ValueError("input must contain a RouteTables array")

    findings: list[dict[str, str]] = []
    summaries: list[dict[str, Any]] = []
    subnet_tables: dict[str, set[str]] = defaultdict(set)
    main_tables: dict[str, set[str]] = defaultdict(set)
    total_routes = 0
    total_defaults = 0
    total_blackholes = 0

    def add_finding(
        severity: str, code: str, resource: str, message: str
    ) -> None:
        findings.append(
            {
                "severity": severity,
                "code": code,
                "resource": resource,
                "message": message,
            }
        )

    for table_index, table in enumerate(tables):
        context = f"RouteTables[{table_index}]"
        if not isinstance(table, dict):
            raise ValueError(f"{context} must be an object")

        table_id = _required_string(table.get("RouteTableId"), "RouteTableId", context)
        vpc_id = _required_string(table.get("VpcId"), "VpcId", context)
        routes = table.get("Routes", [])
        associations = table.get("Associations", [])
        if not isinstance(routes, list):
            raise ValueError(f"{context}.Routes must be an array")
        if not isinstance(associations, list):
            raise ValueError(f"{context}.Associations must be an array")

        tags = table.get("Tags", [])
        name = None
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, dict) and tag.get("Key") == "Name":
                    if isinstance(tag.get("Value"), str):
                        name = tag["Value"]
                    break

        associated_subnets: list[str] = []
        is_main = False
        for assoc_index, association in enumerate(associations):
            assoc_context = f"{context}.Associations[{assoc_index}]"
            if not isinstance(association, dict):
                raise ValueError(f"{assoc_context} must be an object")
            state_object = association.get("AssociationState") or {}
            if not isinstance(state_object, dict):
                raise ValueError(f"{assoc_context}.AssociationState must be an object")
            association_state = str(state_object.get("State", "unknown")).lower()
            is_association_main = association.get("Main") is True
            subnet_id = association.get("SubnetId")

            if is_association_main and association_state == "associated":
                is_main = True
                main_tables[vpc_id].add(table_id)
            if subnet_id:
                subnet_id = _required_string(subnet_id, "SubnetId", assoc_context)
                if association_state == "associated":
                    associated_subnets.append(subnet_id)
                    subnet_tables[subnet_id].add(table_id)
                else:
                    add_finding(
                        "medium",
                        "subnet-association-not-active",
                        table_id,
                        f"Subnet {subnet_id} association state is {association_state!r}",
                    )

        seen_destinations: set[str] = set()
        default_routes: list[dict[str, Any]] = []
        blackhole_count = 0

        for route_index, route in enumerate(routes):
            route_context = f"{context}.Routes[{route_index}]"
            if not isinstance(route, dict):
                raise ValueError(f"{route_context} must be an object")
            try:
                destination, is_default = _route_destination(route, route_context)
            except ValueError as exc:
                add_finding(
                    "high",
                    "invalid-route-destination",
                    table_id,
                    str(exc),
                )
                continue

            if destination in seen_destinations:
                add_finding(
                    "critical",
                    "duplicate-route-destination",
                    table_id,
                    f"Destination {destination} appears more than once in this route table",
                )
            seen_destinations.add(destination)

            state = str(route.get("State", "unknown")).lower()
            target_map = _targets(route)
            route_summary = {
                "destination": destination,
                "state": state,
                "targets": target_map,
            }
            if is_default:
                default_routes.append(route_summary)
            if state == "blackhole":
                blackhole_count += 1
                add_finding(
                    "high",
                    "blackhole-route",
                    table_id,
                    f"Route to {destination} is in blackhole state",
                )
            elif state != "active":
                add_finding(
                    "low",
                    "unknown-route-state",
                    table_id,
                    f"Route to {destination} has state {state!r}",
                )

        if not is_main and not associated_subnets:
            add_finding(
                "info",
                "unassociated-route-table",
                table_id,
                "Route table has no active main or subnet association in this export",
            )

        total_routes += len(routes)
        total_defaults += len(default_routes)
        total_blackholes += blackhole_count
        summaries.append(
            {
                "route_table_id": table_id,
                "vpc_id": vpc_id,
                "name": name,
                "is_main": is_main,
                "associated_subnets": sorted(set(associated_subnets)),
                "route_count": len(routes),
                "default_routes": default_routes,
                "blackhole_route_count": blackhole_count,
            }
        )

    for subnet_id, table_ids in sorted(subnet_tables.items()):
        if len(table_ids) > 1:
            add_finding(
                "critical",
                "subnet-associated-with-multiple-route-tables",
                subnet_id,
                "Subnet is shown as actively associated with route tables: "
                + ", ".join(sorted(table_ids)),
            )

    for vpc_id, table_ids in sorted(main_tables.items()):
        if len(table_ids) > 1:
            add_finding(
                "critical",
                "multiple-main-route-tables",
                vpc_id,
                "Multiple active main route tables are present: "
                + ", ".join(sorted(table_ids)),
            )

    findings.sort(
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]],
            item["code"],
            item["resource"],
            item["message"],
        )
    )
    severity_counts = Counter(item["severity"] for item in findings)

    return {
        "schema_version": 1,
        "summary": {
            "route_table_count": len(summaries),
            "route_count": total_routes,
            "default_route_count": total_defaults,
            "blackhole_route_count": total_blackholes,
            "finding_count": len(findings),
            "severity_counts": {
                severity: severity_counts.get(severity, 0)
                for severity in ("critical", "high", "medium", "low", "info")
            },
        },
        "route_tables": summaries,
        "findings": findings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit an AWS EC2 DescribeRouteTables JSON export offline."
    )
    parser.add_argument("input", type=Path, help="Path to the JSON export")
    parser.add_argument(
        "--output", type=Path, help="Write JSON report to a new file instead of stdout"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing report file (never the input file)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        input_path = args.input
        document = json.loads(input_path.read_text(encoding="utf-8"))
        report = analyse(document)
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"

        if args.output is None:
            sys.stdout.write(rendered)
            return 0

        output_path = args.output
        if output_path.resolve() == input_path.resolve():
            raise ValueError("output path must not be the same as the input path")
        if args.overwrite:
            output_path.write_text(rendered, encoding="utf-8")
        else:
            with output_path.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

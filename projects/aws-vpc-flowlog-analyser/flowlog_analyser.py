#!/usr/bin/env python3
"""Offline analyser for the AWS VPC Flow Logs default version 2 format."""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


EXPECTED_FIELDS = 14
PROTOCOL_NAMES = {
    1: "icmp",
    6: "tcp",
    17: "udp",
    41: "ipv6",
    47: "gre",
    50: "esp",
    58: "icmpv6",
    89: "ospf",
    132: "sctp",
}
VALID_STATUSES = {"OK", "NODATA", "SKIPDATA"}
VALID_ACTIONS = {"ACCEPT", "REJECT"}
MAX_REJECT_EXAMPLES = 20


class FlowLogParseError(ValueError):
    """Raised when a flow-log line cannot be safely interpreted."""


def _integer(value: str, field: str, line_number: int, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise FlowLogParseError(
            f"line {line_number}: {field} must be an integer, got {value!r}"
        ) from exc
    if parsed < minimum:
        raise FlowLogParseError(
            f"line {line_number}: {field} must be >= {minimum}, got {parsed}"
        )
    return parsed


def _optional_port(value: str, field: str, line_number: int) -> int | None:
    if value == "-":
        return None
    port = _integer(value, field, line_number)
    if port > 65535:
        raise FlowLogParseError(
            f"line {line_number}: {field} must be between 0 and 65535"
        )
    return port


def _parse_ip(value: str, field: str, line_number: int) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise FlowLogParseError(
            f"line {line_number}: {field} is not a valid IPv4/IPv6 address: {value!r}"
        ) from exc


def _protocol_name(number: int) -> str:
    return PROTOCOL_NAMES.get(number, f"protocol-{number}")


def parse_record(line: str, line_number: int) -> dict | None:
    """Parse one default-format v2 record; return None for NODATA/SKIPDATA."""
    fields = line.split()
    if len(fields) != EXPECTED_FIELDS:
        raise FlowLogParseError(
            f"line {line_number}: expected {EXPECTED_FIELDS} fields for the default v2 format, got {len(fields)}"
        )

    version = _integer(fields[0], "version", line_number, minimum=1)
    if version != 2:
        raise FlowLogParseError(
            f"line {line_number}: only default version 2 records are supported (got {version})"
        )

    status = fields[13]
    if status not in VALID_STATUSES:
        raise FlowLogParseError(
            f"line {line_number}: unsupported log-status {status!r}; expected OK, NODATA, or SKIPDATA"
        )
    if status != "OK":
        return {"status": status}

    account_id, interface_id = fields[1], fields[2]
    if not account_id.isdigit() or len(account_id) != 12:
        raise FlowLogParseError(
            f"line {line_number}: account-id must contain 12 digits"
        )
    if not interface_id or interface_id == "-":
        raise FlowLogParseError(
            f"line {line_number}: interface-id is required for an OK record"
        )

    src = _parse_ip(fields[3], "srcaddr", line_number)
    dst = _parse_ip(fields[4], "dstaddr", line_number)
    src_port = _optional_port(fields[5], "srcport", line_number)
    dst_port = _optional_port(fields[6], "dstport", line_number)
    protocol_number = _integer(fields[7], "protocol", line_number)
    if protocol_number > 255:
        raise FlowLogParseError(f"line {line_number}: protocol must be between 0 and 255")

    packets = _integer(fields[8], "packets", line_number)
    byte_count = _integer(fields[9], "bytes", line_number)
    start = _integer(fields[10], "start", line_number)
    end = _integer(fields[11], "end", line_number)
    if end < start:
        raise FlowLogParseError(f"line {line_number}: end must be >= start")

    action = fields[12]
    if action not in VALID_ACTIONS:
        raise FlowLogParseError(
            f"line {line_number}: action must be ACCEPT or REJECT for an OK record"
        )

    return {
        "status": status,
        "interface_id": interface_id,
        "srcaddr": src,
        "dstaddr": dst,
        "srcport": src_port,
        "dstport": dst_port,
        "protocol_number": protocol_number,
        "protocol": _protocol_name(protocol_number),
        "packets": packets,
        "bytes": byte_count,
        "start": start,
        "end": end,
        "action": action,
    }


def _ranked(counter: dict, limit: int, *, address_key: str | None = None) -> list[dict]:
    rows = []
    for key, totals in counter.items():
        if address_key:
            row = {address_key: key}
        else:
            protocol, port = key
            row = {"protocol": protocol, "port": port}
        row.update(totals)
        rows.append(row)
    rows.sort(key=lambda row: (-row["bytes"], -row["flows"], str(row.get(address_key or "port"))))
    return rows[:limit]


def analyse_lines(lines: Iterable[str], top_n: int = 5) -> dict:
    """Aggregate flow records into a deterministic, JSON-serialisable report."""
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    status_counts: Counter = Counter()
    action_counts: Counter = Counter({"ACCEPT": 0, "REJECT": 0})
    protocol_counts: Counter = Counter()
    sources: dict = defaultdict(lambda: {"flows": 0, "bytes": 0, "packets": 0})
    destinations: dict = defaultdict(lambda: {"flows": 0, "bytes": 0, "packets": 0})
    destination_ports: dict = defaultdict(lambda: {"flows": 0, "bytes": 0})
    rejected_examples = []
    records_seen = 0
    data_records = 0

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        records_seen += 1
        record = parse_record(raw_line, line_number)
        status_counts[record["status"]] += 1
        if record["status"] != "OK":
            continue

        data_records += 1
        action_counts[record["action"]] += 1
        protocol_counts[record["protocol"]] += 1

        for table, key in ((sources, record["srcaddr"]), (destinations, record["dstaddr"])):
            table[key]["flows"] += 1
            table[key]["bytes"] += record["bytes"]
            table[key]["packets"] += record["packets"]

        if record["dstport"] is not None:
            key = (record["protocol"], record["dstport"])
            destination_ports[key]["flows"] += 1
            destination_ports[key]["bytes"] += record["bytes"]

        if record["action"] == "REJECT" and len(rejected_examples) < MAX_REJECT_EXAMPLES:
            rejected_examples.append(
                {
                    "interface_id": record["interface_id"],
                    "srcaddr": record["srcaddr"],
                    "dstaddr": record["dstaddr"],
                    "dstport": record["dstport"],
                    "protocol": record["protocol"],
                    "bytes": record["bytes"],
                    "start": record["start"],
                    "end": record["end"],
                }
            )

    return {
        "schema": "aws-vpc-flow-logs-default-v2",
        "records_seen": records_seen,
        "data_records": data_records,
        "status_counts": {status: status_counts[status] for status in sorted(VALID_STATUSES) if status_counts[status]},
        "action_counts": {action: action_counts[action] for action in sorted(VALID_ACTIONS)},
        "protocol_counts": dict(sorted(protocol_counts.items())),
        "top_sources": _ranked(sources, top_n, address_key="address"),
        "top_destinations": _ranked(destinations, top_n, address_key="address"),
        "top_destination_ports": _ranked(destination_ports, top_n),
        "rejected_flow_examples": rejected_examples,
        "rejected_flow_examples_truncated": action_counts["REJECT"] > len(rejected_examples),
    }


def analyse_file(path: Path, top_n: int = 5) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            report = analyse_lines(handle, top_n=top_n)
    except OSError as exc:
        raise FlowLogParseError(f"cannot read input file {path}: {exc}") from exc
    report["input_file"] = path.name
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarise AWS VPC Flow Logs in the default version 2 format (offline)."
    )
    parser.add_argument("input", type=Path, help="path to a UTF-8 flow-log text file")
    parser.add_argument("--top", type=int, default=5, help="number of entries in each top-N table (default: 5)")
    parser.add_argument("--output", type=Path, help="write JSON report to this path instead of stdout")
    parser.add_argument("--overwrite", action="store_true", help="allow replacing an existing --output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")

    try:
        report = analyse_file(args.input, top_n=args.top)
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.resolve() == args.input.resolve():
                raise FlowLogParseError("output path must not be the same as the input path")
            if args.output.exists() and not args.overwrite:
                raise FlowLogParseError(
                    f"output file already exists: {args.output} (pass --overwrite to replace it)"
                )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"Wrote report to {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(rendered)
        return 0
    except (FlowLogParseError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Audit normalized BGP peer snapshots without live device access."""
import argparse
import csv
import json
import sys
from pathlib import Path

FIELDS = ["device", "peer", "remote_as", "state", "expected_state",
          "prefixes_received", "status", "findings"]


def non_negative_int(value, label, optional=False):
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def validate_snapshot(payload):
    if not isinstance(payload, dict):
        raise ValueError("Top-level JSON value must be an object")
    devices = payload.get("devices")
    if not isinstance(devices, list) or not devices:
        raise ValueError("'devices' must be a non-empty list")
    for di, device in enumerate(devices):
        p = f"devices[{di}]"
        if not isinstance(device, dict):
            raise ValueError(f"{p} must be an object")
        if not isinstance(device.get("name"), str) or not device["name"].strip():
            raise ValueError(f"{p}.name must be a non-empty string")
        peers = device.get("peers")
        if not isinstance(peers, list):
            raise ValueError(f"{p}.peers must be a list")
        seen = set()
        for pi, peer in enumerate(peers):
            q = f"{p}.peers[{pi}]"
            if not isinstance(peer, dict):
                raise ValueError(f"{q} must be an object")
            address = peer.get("address")
            if not isinstance(address, str) or not address.strip():
                raise ValueError(f"{q}.address must be a non-empty string")
            if address in seen:
                raise ValueError(f"{p} contains duplicate peer address {address!r}")
            seen.add(address)
            non_negative_int(peer.get("remote_as"), f"{q}.remote_as")
            if not isinstance(peer.get("state"), str) or not peer["state"].strip():
                raise ValueError(f"{q}.state must be a non-empty string")
            expected = peer.get("expected_state", "Established")
            if not isinstance(expected, str) or not expected.strip():
                raise ValueError(f"{q}.expected_state must be a non-empty string")
            prefixes = non_negative_int(peer.get("prefixes_received"),
                                        f"{q}.prefixes_received", optional=True)
            minimum = non_negative_int(peer.get("min_prefixes"),
                                       f"{q}.min_prefixes", optional=True)
            maximum = non_negative_int(peer.get("max_prefixes"),
                                       f"{q}.max_prefixes", optional=True)
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"{q}.min_prefixes cannot exceed max_prefixes")
    return payload


def audit_snapshot(payload):
    snapshot = validate_snapshot(payload)
    rows = []
    for device in snapshot["devices"]:
        for peer in device["peers"]:
            state = peer["state"]
            expected = peer.get("expected_state", "Established")
            prefixes = peer.get("prefixes_received")
            minimum, maximum = peer.get("min_prefixes"), peer.get("max_prefixes")
            findings, status = [], "PASS"
            if state.casefold() != expected.casefold():
                findings.append(f"state is {state}; expected {expected}")
                status = "FAIL"
            if prefixes is None and (minimum is not None or maximum is not None):
                findings.append("prefix count unavailable for configured threshold")
                if status != "FAIL":
                    status = "WARN"
            elif prefixes is not None:
                if minimum is not None and prefixes < minimum:
                    findings.append(f"received {prefixes} prefixes; minimum is {minimum}")
                    status = "FAIL"
                if maximum is not None and prefixes > maximum:
                    findings.append(f"received {prefixes} prefixes; maximum is {maximum}")
                    status = "FAIL"
            rows.append({
                "device": device["name"], "peer": peer["address"],
                "remote_as": peer["remote_as"], "state": state,
                "expected_state": expected,
                "prefixes_received": "" if prefixes is None else prefixes,
                "status": status,
                "findings": "; ".join(findings) if findings else "No issues detected",
            })
    return rows


def print_table(rows):
    columns = [("device", "DEVICE"), ("peer", "PEER"), ("state", "STATE"),
               ("prefixes_received", "PREFIXES"), ("status", "STATUS")]
    widths = {key: max([len(label)] + [len(str(row[key])) for row in rows])
              for key, label in columns}
    print("  ".join(label.ljust(widths[key]) for key, label in columns))
    print("  ".join("-" * widths[key] for key, _ in columns))
    for row in rows:
        print("  ".join(str(row[key]).ljust(widths[key]) for key, _ in columns))
        if row["findings"] != "No issues detected":
            print(f"    Finding: {row['findings']}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Audit normalized BGP peer state and received-prefix thresholds.")
    parser.add_argument("input", nargs="?", default="sample.json",
                        help="JSON snapshot file (default: sample.json)")
    parser.add_argument("--output", help="optional path to write detailed CSV results")
    args = parser.parse_args(argv)
    try:
        with Path(args.input).open(encoding="utf-8") as stream:
            rows = audit_snapshot(json.load(stream))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    print_table(rows)
    if args.output:
        try:
            with Path(args.output).open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            print(f"Output error: {exc}", file=sys.stderr)
            return 2
        print(f"\nDetailed CSV report written to {args.output}")
    failed = sum(row["status"] == "FAIL" for row in rows)
    warnings = sum(row["status"] == "WARN" for row in rows)
    print(f"\nSummary: {len(rows)} peers, {failed} failed, {warnings} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

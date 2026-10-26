# BGP Peer Health Audit

A small, offline Python tool that audits normalized BGP neighbor snapshots for session-state mismatches and unexpected received-prefix counts. It complements the general network-health report with routing-specific checks.

## What it checks

- Whether each peer is in its expected state (defaults to Established)
- Optional minimum and maximum received-prefix thresholds
- Missing prefix telemetry (reported as WARN when a threshold was configured)
- Malformed input and duplicate peer addresses within a device

The input is a vendor-neutral JSON format so snapshots can be prepared from lab output, NAPALM/Netmiko scripts, APIs, or manually sanitized data. This project does not connect to routers or collect data itself.

## Requirements

- Python 3.10 or newer
- Python standard library only; no third-party packages required

## Run the healthy sample

From this directory:

    python report.py sample.json
    python report.py sample.json --output report.csv

The healthy sample should finish with exit code 0. The optional CSV contains one row per peer and a findings column.

## Exercise alert conditions

    python report.py sample-alerts.json

This intentionally unhealthy sample contains a non-established peer and a prefix count below its configured minimum. The script should return exit code 1, which is useful for CI or scheduled checks. Invalid input or file errors return exit code 2.

Run the unit tests:

    python -m unittest -v

## Input format

Each device has a name and a peers list. Each peer requires address, integer remote_as, and string state. Optional fields are expected_state, prefixes_received, min_prefixes, and max_prefixes.

Example:

    {
      "devices": [
        {
          "name": "edge-r1",
          "peers": [
            {
              "address": "192.0.2.2",
              "remote_as": 65020,
              "state": "Established",
              "prefixes_received": 120,
              "min_prefixes": 100,
              "max_prefixes": 150
            }
          ]
        }
      ]
    }

## Safety and limitations

- Samples use documentation-only IP addresses and private-use ASNs.
- The tool only audits supplied snapshots; it does not authenticate to devices, modify routing, or change production state.
- Prefix thresholds must be chosen for the specific peer and routing policy. Legitimate maintenance or policy changes can cause alerts.
- Normalized data must be collected and reviewed securely. Do not commit customer configurations, real peer addresses, credentials, or internal topology.
- Session-state and prefix checks are a basic signal, not a substitute for routing-table, RPKI, policy, reachability, or change-window validation.
- Tested locally with synthetic inputs; no live network or vendor integration is included.

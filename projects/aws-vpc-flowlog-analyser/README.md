# AWS VPC Flow Log Analyser

An offline, standard-library Python utility for summarising **AWS VPC Flow Logs in the default version 2 format**. It turns synthetic or sanitised flow records into a compact JSON report covering accepted/rejected traffic, protocol counts, top source/destination addresses, destination ports, and a bounded sample of rejected flows.

This project complements the portfolio's network-health report (probe availability), BGP peer audit (routing state), and IPAM overlap auditor (address-plan quality). It focuses on traffic observations rather than device state or reachability probes.

## Architecture and data flow

```text
VPC Flow Logs text export
        |
        v
Strict 14-field / version-2 parser
        |
        +--> Validate IPs, ports, protocol, counters and timestamps
        |
        +--> Count NODATA / SKIPDATA separately
        |
        v
In-memory aggregation (no external calls)
        |
        v
JSON report: actions, protocols, top talkers, destination ports, rejected examples
```

The parser uses Python's `ipaddress`, `argparse`, `json`, and collection types. It does not query AWS, download logs, enrich addresses, infer security-group rules, or change network resources. `REJECT` means the flow was rejected by the VPC networking path represented in the log; the report does not identify the exact control responsible.

## Prerequisites

- Python 3.10 or newer.
- No third-party dependencies, AWS credentials, cloud account, or network access.
- A UTF-8 text file containing AWS VPC Flow Logs in the default version 2 field order.

## Safe setup and run

Clone the repository and enter this directory:

```bash
git clone https://github.com/ahsansid23/cloud-network-engineering.git
cd cloud-network-engineering/projects/aws-vpc-flowlog-analyser
python flowlog_analyser.py sample-flow-logs.txt
```

Write a report to a new file:

```bash
python flowlog_analyser.py sample-flow-logs.txt --output report.json
```

The tool refuses to replace an existing output file unless `--overwrite` is supplied. It also refuses to use the input file as the output path. To change the number of entries in each top-N list:

```bash
python flowlog_analyser.py sample-flow-logs.txt --top 10
```

Use synthetic data first. If analysing real exports, process them locally in an approved environment, restrict file permissions, and do not commit raw logs or generated reports to a public repository. Flow logs can expose internal addresses, interface identifiers, traffic patterns, and workload relationships.

## Input format

The parser expects exactly these 14 whitespace-separated fields, in this order:

`version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status`

It supports the default version 2 schema only. `OK` records are validated and aggregated. `NODATA` and `SKIPDATA` records are counted but excluded from traffic totals. A dash (`-`) is accepted for source/destination ports, which is useful for ICMP-style traffic. IPv4 and IPv6 addresses are accepted.

The included `sample-flow-logs.txt` uses documentation-only public addresses (`203.0.113.0/24`, `198.51.100.0/24`), RFC 1918 private addresses, a synthetic account ID, and a placeholder interface ID. It intentionally includes both `ACCEPT` and `REJECT`, plus `NODATA` and `SKIPDATA` examples.

## Report fields

| Field | Meaning |
|---|---|
| `records_seen` | Non-empty input lines, including NODATA/SKIPDATA |
| `data_records` | Valid `OK` records included in traffic aggregates |
| `status_counts` | Counts for `OK`, `NODATA`, and `SKIPDATA` observed in the file |
| `action_counts` | `ACCEPT` and `REJECT` flow counts |
| `protocol_counts` | Flow counts grouped by protocol name/number |
| `top_sources` / `top_destinations` | Addresses ranked by bytes, then flow count |
| `top_destination_ports` | Protocol/port pairs ranked by bytes, then flow count |
| `rejected_flow_examples` | Up to 20 rejected flow summaries, in input order |
| `rejected_flow_examples_truncated` | Whether more rejected flows existed than the example limit |

Top-N output is a ranking aid, not a risk score. Byte and packet totals reflect the records provided and the aggregation window represented by those records.

## Validation

Run the offline unit tests:

```bash
python -m unittest -v
```

Run the sample and inspect the JSON:

```bash
python flowlog_analyser.py sample-flow-logs.txt
```

The sample should report 8 records seen, 6 `OK` data records, 4 accepted flows, 2 rejected flows, 1 `NODATA`, and 1 `SKIPDATA`. The tests cover IPv4 and IPv6 parsing, ICMP records without ports, status handling, malformed field counts, unsupported versions, invalid addresses/ports, timestamp ordering, aggregation, CLI JSON output, and output-file overwrite protection.

## Failure handling and exit codes

- `0`: report generated successfully.
- `2`: input/format/output error or invalid command-line option.

Malformed `OK` records fail the run with a line number rather than producing a partial report. This is intentional: incomplete input should not silently look like a complete traffic picture.

## Limitations and next steps

- Only the default version 2 field order is supported. Custom field order, custom format strings, and versions with additional fields are rejected rather than guessed.
- The parser expects one record per line and does not decompress files, read S3, query CloudWatch, or process Parquet.
- It does not model aggregation intervals, ENI ownership, NAT translation context, security-group/NACL rule evaluation, route tables, or cross-account identity.
- It does not distinguish application errors from network policy drops, and a missing record is not proof that traffic did not occur.
- `NODATA` and `SKIPDATA` are reported because they affect the completeness of the observation window; they are not treated as accepted or rejected flows.
- Large exports are aggregated in memory. For very large datasets, use streaming output, partitioned aggregation, or a query engine such as Athena.
- Tests use synthetic fixtures only. No AWS account, S3 bucket, live flow-log delivery, or production traffic has been tested.

Before using results in an incident or security investigation, confirm the configured Flow Logs format, capture scope, aggregation interval, delivery health, and relevant AWS networking controls. Treat the report as an investigative aid, not proof of root cause.

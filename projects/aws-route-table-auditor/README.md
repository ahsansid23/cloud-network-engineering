# AWS Route Table Auditor

An offline Python utility for reviewing JSON exports from the AWS EC2 `DescribeRouteTables` API. It highlights route-table conditions that are easy to miss during VPC reviews: blackhole routes, duplicate destinations, unusual subnet associations, and unused route tables.

This project complements the Terraform VPC reference architecture (intended routing design) and the VPC Flow Log analyser (observed traffic). It checks exported control-plane routing configuration; it does not test data-plane reachability.

## Architecture and design

```text
AWS EC2 DescribeRouteTables JSON export
                  |
                  v
       Input/schema validation
                  |
                  v
      Route and association analysis
        |         |          |
        |         |          +--> main/subnet association checks
        |         +-------------> default route and target summary
        +-----------------------> CIDR canonicalisation, duplicates,
                                   blackhole and route-state checks
                  |
                  v
         Deterministic JSON report
```

The tool uses only the Python standard library. It reads one local JSON file and performs no AWS API calls, authentication, DNS lookups, network probes, or infrastructure changes.

### Checks performed

| Finding | Severity | Meaning |
|---|---|---|
| `blackhole-route` | High | AWS reports a route as `blackhole`, so its target is unavailable |
| `duplicate-route-destination` | Critical | The same canonical CIDR or prefix-list destination appears more than once in one route table |
| `subnet-associated-with-multiple-route-tables` | Critical | The export shows one subnet actively associated with multiple route tables |
| `multiple-main-route-tables` | Critical | The export shows multiple active main route tables for one VPC |
| `invalid-route-destination` | High | A route has a missing, ambiguous, or invalid destination |
| `subnet-association-not-active` | Medium | A subnet association is not in the `associated` state |
| `unknown-route-state` | Low | A route state is missing or is not `active` / `blackhole` |
| `unassociated-route-table` | Info | No active main or subnet association is present in this export |

Default routes (`0.0.0.0/0` and `::/0`) are listed with their targets, but are not automatically treated as unsafe. An Internet Gateway, NAT Gateway, Transit Gateway, egress-only Internet Gateway, or other target may be correct depending on the intended design.

## Prerequisites

- Python 3.10 or newer.
- No third-party packages.
- A JSON export with the `RouteTables` array returned by AWS EC2 `DescribeRouteTables`.
- No AWS account, credentials, IAM permissions, or live network access are required to run the analyser.

To create an export in an approved AWS environment, an operator with suitable read permissions can run:

```bash
aws ec2 describe-route-tables --output json > route-tables.json
```

This AWS CLI command is shown as an optional data-collection step only; the project itself never runs it. Scope and protect exports because they reveal VPC IDs, subnet associations, CIDRs, and routing targets. Do not commit real exports to a public repository.

## Safe setup and run

Clone the repository and enter the project directory:

```bash
git clone https://github.com/ahsansid23/cloud-network-engineering.git
cd cloud-network-engineering/projects/aws-route-table-auditor
```

Run against the synthetic fixture first:

```bash
python route_table_auditor.py sample-route-tables.json
```

Write the report to a new file:

```bash
python route_table_auditor.py sample-route-tables.json --output report.json
```

The tool refuses to replace an existing report. Use `--overwrite` only when you explicitly intend to replace that report:

```bash
python route_table_auditor.py sample-route-tables.json --output report.json --overwrite
```

The input file can never be used as the output path, even with `--overwrite`. The tool does not modify the input or any AWS resource.

## Input and output

The input is the JSON object returned by `DescribeRouteTables`, including a top-level `RouteTables` array. It uses route fields such as `DestinationCidrBlock`, `DestinationIpv6CidrBlock`, `DestinationPrefixListId`, `GatewayId`, `NatGatewayId`, `TransitGatewayId`, and `State`, plus table and association identifiers.

The report contains:

- `summary`: route-table, route, default-route and blackhole totals, plus finding counts by severity.
- `route_tables`: VPC/table identifiers, optional Name tag, active subnet associations, default routes and blackhole count.
- `findings`: deterministic severity/code/resource/message records suitable for review or later integration.

IPv4 and IPv6 CIDRs are canonicalised before duplicate detection. Managed prefix-list destinations are compared by prefix-list ID because the export does not include the prefix list's expanded CIDR contents.

## Validation

Run the unit tests from this directory:

```bash
python -m unittest -v
```

Compile the implementation:

```bash
python -m py_compile route_table_auditor.py test_route_table_auditor.py
```

Run the sample and validate the generated JSON:

```bash
python route_table_auditor.py sample-route-tables.json --output /tmp/route-table-report.json
python -m json.tool /tmp/route-table-report.json
```

The synthetic sample contains three route tables, six routes, two default routes, one blackhole route, and one unassociated route table. Expected findings are one `blackhole-route` (high) and one `unassociated-route-table` (info). The fixture uses private/documentation-only addressing and fabricated resource identifiers.

## Exit codes

- `0`: input parsed and report generated. Findings are report content, not a process failure.
- `2`: invalid input, unreadable file, invalid output path, or refused overwrite.

## Limitations and operational cautions

- This is an offline snapshot auditor, not a live AWS inventory tool. The result is only as complete and current as the supplied export.
- It does not verify IAM, security groups, network ACLs, DNS, NAT health, Transit Gateway route tables, VPC peering state, firewall policy, or end-to-end reachability.
- It does not resolve managed prefix lists into their CIDRs or determine whether a default route is appropriate for a workload.
- A blackhole route is reported from the API's `State`; the tool does not infer the cause or repair it.
- Unassociated route tables may be intentionally staged or retained. Review context before treating an informational finding as a fault.
- Multiple association findings are evaluated from the supplied snapshot. If the export was filtered, stale, or collected during a change, corroborate it before acting.
- Synthetic unit tests do not prove compatibility with every AWS API version, partition, or future response variation. No live AWS account or deployment has been tested.

Use findings as review prompts, not automatic remediation instructions. Confirm route intent with the network design, change record, and current AWS documentation before making changes.

# Cloud Network Engineering Portfolio

A hands-on portfolio of cloud networking, infrastructure as code, network automation, and operational validation. Projects are deliberately small enough to review, explain, and test; examples are learning artifacts, not claims of production deployment or employer work.

## Project catalogue

| Project | Focus | Skills demonstrated |
|---|---|---|
| [AWS VPC reference architecture](projects/aws-vpc-terraform/) | Terraform network foundation | VPC, public/private subnets, route tables, security-group boundaries, plan review |
| [OpenShift network policy](projects/openshift-network-policy/) | Application connectivity and isolation | Deployment, Service, Route, pod selection, ingress policy, TLS termination |
| [Ansible configuration backup](projects/ansible-config-backup/) | Network automation | Network CLI, configuration collection, local file permissions, secret handling |
| [Network health report](projects/network-health-report/) | Availability metrics | CSV ingestion, availability calculation, packet-loss reporting |
| [BGP peer health audit](projects/bgp-peer-audit/) | Routing operations | Session-state checks, prefix thresholds, normalized snapshots, offline vendor parsers |
| [IPAM overlap auditor](projects/ipam-overlap-auditor/) | Address-plan quality | IPv4/IPv6 CIDR validation, duplicate and containment findings, site/VRF scope, JSON output |

## How to use this portfolio

1. Start with the project README and understand the design before running commands.
2. Use supplied synthetic fixtures first; they are intentionally safe and may include expected findings.
3. Run offline validation where provided. A documented command is not evidence that it has been executed in your environment.
4. For infrastructure projects, inspect the plan/manifests and provider or cluster prerequisites before any apply.
5. Never commit secrets, customer data, real device configurations, or internal addressing/topology. Use a secret manager or encrypted vault for credentials.

## Validation philosophy

- **Offline first:** prefer unit tests, sample inputs, syntax checks, and plans that do not create resources.
- **Fail clearly:** document expected exit codes and intentional sample failures.
- **Explicit limitations:** synthetic tests do not prove vendor compatibility, production readiness, cloud-provider behavior, or live network reachability.
- **Review before change:** these tools report or describe candidate configurations; they do not replace peer review, change control, backup/rollback planning, or operational approval.

## Suggested learning path

1. Build CIDR and subnetting intuition with the IPAM auditor.
2. Understand routing adjacency health with the BGP peer audit.
3. Correlate reachability-style metrics with the network health report.
4. Review how Terraform models cloud network boundaries.
5. Explore application-level segmentation in OpenShift.
6. Study the Ansible backup workflow and its operational safeguards.

All examples are for education and controlled labs. Validate against current vendor documentation and your own requirements before adapting them to a real environment.

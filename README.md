# Cloud Network Engineering Portfolio

Practical demo projects for cloud networking, automation, and network operations. These are portfolio/lab examples, not claims of production deployment or employer work.

## Projects
- [OpenShift application networking and isolation](projects/openshift-network-policy/): Route, service, deployment, and scoped Kubernetes NetworkPolicy.
- [AWS VPC reference architecture (Terraform)](projects/aws-vpc-terraform/): segmented public/private subnets and routing.
- [Network configuration backup (Ansible)](projects/ansible-config-backup/): lab playbook example; use Ansible Vault or a secret manager for credentials.
- [Network health report (Python)](projects/network-health-report/): offline availability and packet-loss summary from synthetic CSV input.
- [BGP peer health audit (Python)](projects/bgp-peer-audit/): offline BGP session-state and received-prefix threshold checks with CSV output and unit tests.
- [IPAM overlap auditor (Python)](projects/ipam-overlap-auditor/): offline IPv4/IPv6 inventory validation, duplicate detection, and overlap checks scoped by site and VRF.

Review and test each project before use. Remove secrets, customer data, and internal network details before publishing.

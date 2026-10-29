# AWS VPC reference architecture (Terraform)

A small Terraform example for an AWS VPC with public and private subnets, an Internet Gateway, separate route tables, and a scoped SSH ingress rule. It demonstrates resource relationships and routing intent; it is not a complete production landing zone.

## Architecture and traffic flow

- One VPC using a configurable IPv4 CIDR.
- Public subnets associated with a shared route table that has a default route to an Internet Gateway.
- Private subnets each associated with their own route table. No default route or NAT Gateway is configured.
- One security group allows TCP/22 only from `admin_cidr`.
- DNS support and DNS hostnames are enabled.

The word *public* means the subnet's route table can route IPv4 traffic to an Internet Gateway; it does not make every resource publicly reachable. A workload still needs suitable addressing plus security-group and network ACL permission. The example does not create EC2 instances.

## Prerequisites

- Terraform 1.5 or newer.
- AWS CLI credentials configured using an approved profile or role; do not put access keys in Terraform files.
- An AWS account/region with permission to create VPC, subnet, route, Internet Gateway, and security-group resources.
- Review current AWS pricing and quotas before any apply.

## Static checks and plan review

```bash
terraform fmt -check
terraform init -backend=false
terraform validate
terraform plan -var='admin_cidr=203.0.113.10/32'
```

The plan command may need AWS credentials and network access because the configuration queries availability zones. A plan is not a deployment, but it can expose configuration or provider issues. The documentation-only default is not a usable administrator address.

## Cost and safety

- Do **not** run `terraform apply` without reviewing the complete plan and obtaining required approval.
- NAT is deliberately omitted to avoid unexpected hourly/data-processing charges. Private subnets therefore have no general outbound Internet route.
- The configuration creates network resources that may incur charges in some circumstances; do not assume deployment is free.
- The SSH security group is a teaching artifact and is not attached to an instance. For production, prefer Systems Manager Session Manager or a managed access path where possible.
- Keep Terraform state private: it can contain infrastructure metadata and sensitive values. Never commit state files, plans, credentials, or real environment values.

## Limitations and next steps

This is a reference skeleton, not a production design. It does not include IPv6, VPC endpoints, flow logs, Network Firewall, centralized egress, NAT, private DNS design, multi-account boundaries, endpoint policies, custom NACLs, or workload resources. It also lacks explicit preconditions for CIDR overlap and availability-zone count. Validate CIDRs, subnet sizing, region support, route intent, IAM permissions, and cost before extending it.

No live AWS deployment or cost test is claimed by this repository.

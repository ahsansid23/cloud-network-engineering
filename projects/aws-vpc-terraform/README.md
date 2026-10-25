# AWS VPC reference architecture

Terraform starter for a VPC with public and private subnets across availability zones. NAT is omitted to avoid surprise cost. Run `terraform init`, `terraform fmt -check`, `terraform validate`, then `terraform plan -var='admin_cidr=YOUR_PUBLIC_IP/32'`. Review the plan and costs before applying.

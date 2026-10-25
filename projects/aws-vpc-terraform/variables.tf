variable "aws_region" {
  type    = string
  default = "eu-west-2"
}
variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}
variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.40.1.0/24", "10.40.2.0/24"]
}
variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.40.11.0/24", "10.40.12.0/24"]
}
variable "admin_cidr" {
  type        = string
  description = "Trusted administrator IP CIDR"
  default     = "203.0.113.10/32"
}

variable "vpc_cidr_block" {
  default = "10.10.0.0/16"
}
variable "private_subnet1_cidr_block" {
  default = "10.10.128.0/20"
}
variable "private_subnet2_cidr_block" {
  default = "10.10.144.0/20"
}
variable "public_subnet1_cidr_block" {
  default = "10.10.0.0/20"
}
variable "public_subnet2_cidr_block" {
  default = "10.10.16.0/20"
}

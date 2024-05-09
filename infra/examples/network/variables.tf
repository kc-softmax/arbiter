variable "vpc_cidr_block" {
  default = "10.20.0.0"
}
variable "vpc_subnet_mask" {
  default = "16"
}
variable "public_subnet1" {
  default = "10.20.0.0"
}
variable "public_subnet2" {
  default = "10.20.16.0"
}
variable "private_subnet1" {
  default = "10.20.128.0"
}
variable "private_subnet2" {
  default = "10.20.144.0"
}
variable "subnet_mask" {
  default = "20"
}
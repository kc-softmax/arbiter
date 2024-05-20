variable "service_name" {
  description = "input your service name"
  type        = string
}
variable "cidr" {
  description = "vpc cidr block"
  type        = string
}
variable "region" {
  description = "specific deployment region"
  type        = string
}
variable "instance_type" {
  description = "instance type(t3.medium, c5.large)"
  type        = string
}
variable "cache_node_type" {
  description = "cache node type(cache.t3.small)"
  type = string
}
variable "zone_name" {
  description = "domain"
  type        = string
}
variable "record_name" {
  description = "host"
  type        = string
}
variable "key_pair" {
  description = "key pair for ssh connect"
  type        = string
}

variable "service_name" {
  type = string
}
variable "service_list" {
  type = map(string)
}
variable "cidr" {
  type = string
}
variable "region" {
  type = string
}
variable "instance_type" {
  type = string
}
variable "cache_node_type" {
  type = string
}
variable "zone_name" {
  type = string
}
variable "record_name" {
  type = string
}
variable "key_pair" {
  type = string
}

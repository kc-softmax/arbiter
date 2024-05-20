variable "service_name" {}
variable "private_subnet1_id" {}
variable "private_subnet2_id" {}
variable "redis_sg_id" {}
variable "cache_node_type" {}
variable "engine" {
  default = "redis"
}
variable "engine_version" {
  default = "7.1"
}
variable "parameter_group_name" {
  default = "default.redis7"
}

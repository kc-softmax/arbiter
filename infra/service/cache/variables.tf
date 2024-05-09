variable "example_private_subnet1_id" {}
variable "example_private_subnet2_id" {}
variable "example_redis_sg" {}
variable "engine" {
  default = "redis"
}
variable "engine_version" {
  default = "7.1"
}
variable "node_type" {
  default = "cache.t3.small"
}
variable "parameter_group_name" {
  default = "default.redis7"
}

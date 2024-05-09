variable "example_public_subnet1_id" {}
variable "example_public_subnet2_id" {}
variable "example_rds_sg" {}
variable "engine" {
  default = "aurora-postgresql"
}
variable "engine_version" {
  default = "15.4"
}

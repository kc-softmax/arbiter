variable "example_sg_id" {}
variable "example_public_subnet1_id" {}
variable "example_public_subnet2_id" {}
variable "example_cluster" {}
variable "example_tg" {}
variable "image_id" {
  default = "ami-050a4617492ff5822"
}
variable "instance_type" {
  default = "t3.small"
}
variable "key_name" {
  default = "kc-softmax-ap-norheast-2-211220"
}

variable "service_name" {}
variable "ec2_sg_id" {}
variable "public_subnet1_id" {}
variable "public_subnet2_id" {}
variable "cluster" {}
variable "ec2_tg" {}
variable "instance_type" {}
variable "key_pair" {}
variable "image_id" {
  default = "ami-050a4617492ff5822"
}

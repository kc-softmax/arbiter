variable "service_name" {}
variable "ec2_tg" {}
variable "alb" {}
variable "image_url" {}
variable "region" {}
variable "task_exec_role_arn" {
  default = "arn:aws:iam::669354009400:role/ecsTaskExecutionRole"
}
variable "launch_type" {
  default = "EC2"
}
variable "iam_role" {
  default = "arn:aws:iam::669354009400:role/ecsServiceRole"
}
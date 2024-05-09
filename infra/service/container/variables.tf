variable "example_tg" {}
variable "example_alb" {}
variable "image_uri" {}
variable "task_exec_role_arn" {
  default = "arn:aws:iam::669354009400:role/ecsTaskExecutionRole"
}
variable "launch_type" {
  default = "EC2"
}
variable "iam_role" {
  default = "arn:aws:iam::669354009400:role/ecsServiceRole"
}

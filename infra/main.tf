variable "key_name" {}

module "service" {
  source = "./service"
}

module "examples" {
  source = "./examples"
}


module "service" {
  source = "./service"

  cidr = var.cidr
  region = var.region
  instance_type = var.instance_type
  zone_name = var.zone_name
  record_name = var.record_name
}

# module "examples" {
#   source = "./examples"
# }

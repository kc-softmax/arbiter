module "service" {
  source = "./service"

  service_name  = var.service_name
  cidr          = var.cidr
  region        = var.region
  instance_type = var.instance_type
  cache_node_type = var.cache_node_type
  zone_name     = var.zone_name
  record_name   = var.record_name
  key_pair      = var.key_pair
}

# module "examples" {
#   source = "./examples"
# }

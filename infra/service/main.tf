module "network" {
  source = "./network"

  service_name   = var.service_name
  vpc_cidr_block = var.cidr
}

module "sg" {
  source = "./sg"

  service_name = var.service_name
  vpc_id       = module.network.vpc_id
}

module "lb" {
  source = "./lb"

  service_name      = var.service_name
  service_list      = var.service_list
  vpc_id            = module.network.vpc_id
  public_subnet1_id = module.network.public_subnet1_id
  public_subnet2_id = module.network.public_subnet2_id
  alb_sg_id         = module.sg.alb_sg_id
  zone_name         = var.zone_name
}

module "compute" {
  source = "./compute"

  service_name      = var.service_name
  service_list      = var.service_list
  ec2_sg_id         = module.sg.ec2_sg_id
  public_subnet1_id = module.network.public_subnet1_id
  public_subnet2_id = module.network.public_subnet2_id
  cluster           = module.container.cluster
  ec2_tg            = module.lb.ec2_tg
  instance_type     = var.instance_type
  key_pair          = var.key_pair
}

module "images" {
  source       = "./images"
  service_name = var.service_name
  service_list = var.service_list
}

module "container" {
  source = "./container"

  service_name          = var.service_name
  service_list          = var.service_list
  ec2_tg                = module.lb.ec2_tg
  alb                   = module.lb.alb
  service_image_url_map = module.images.service_image_url_map
  arbiter_image_url     = module.images.arbiter_image_url
  region                = var.region
}

module "cache" {
  source = "./cache"

  service_name       = var.service_name
  redis_sg_id        = module.sg.redis_sg_id
  private_subnet1_id = module.network.private_subnet1_id
  private_subnet2_id = module.network.private_subnet2_id
  cache_node_type    = var.cache_node_type
}

# module "rds" {
#   source = "./rds"

#   service_name = var.service_name
#   example_public_subnet1_id = module.network.example_public_subnet1_id
#   example_public_subnet2_id = module.network.example_public_subnet2_id
#   example_rds_sg = module.sg.example_rds_sg
# }

module "domain" {
  source = "./domain"

  alb         = module.lb.alb
  zone_name   = var.zone_name
  record_name = var.record_name
}
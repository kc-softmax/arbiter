module "network" {
  source = "./network"
}

module "sg" {
  source         = "./sg"
  example_vpc_id = module.network.example_vpc_id
}

module "lb" {
  source                    = "./lb"
  example_vpc               = module.network.example_vpc_id
  example_public_subnet1_id = module.network.example_public_subnet1_id
  example_public_subnet2_id = module.network.example_public_subnet2_id
  example_sg                = module.sg.example_sg
}

module "compute" {
  source                    = "./compute"
  example_sg_id             = module.sg.example_sg
  example_public_subnet1_id = module.network.example_public_subnet1_id
  example_public_subnet2_id = module.network.example_public_subnet2_id
  example_cluster           = module.container.example_cluster
  example_tg                = module.lb.example_tg
}

module "images" {
  source = "./images"
}

module "container" {
  source      = "./container"
  example_tg  = module.lb.example_tg
  example_alb = module.lb.example_alb
  image_uri = module.images.image_uri
}

module "cache" {
    source = "./cache"
    example_redis_sg = module.sg.example_redis_sg
    example_private_subnet1_id = module.network.example_private_subnet1_id
    example_private_subnet2_id = module.network.example_private_subnet2_id
}

# module "rds" {
#   source = "./rds"
#   example_public_subnet1_id = module.network.example_public_subnet1_id
#   example_public_subnet2_id = module.network.example_public_subnet2_id
#   example_rds_sg = module.sg.example_rds_sg
# }

module "domain" {
  source      = "./domain"
  example_elb = module.lb.example_alb
}
module "network" {
  source = "./network"
}

module "sg" {
  source         = "./sg"
  example_vpc_id = module.network.example_vpc_id
}

module "lb" {
  source                    = "./lb"
  example-vpc               = module.network.example_vpc_id
  example-public-subnet1-id = module.network.example_public_subnet1_id
  example-public-subnet2-id = module.network.example_public_subnet2_id
  example-sg                = module.sg.example-sg
}

module "compute" {
  source                    = "./compute"
  example-sg-id             = module.sg.example-sg
  example-public-subnet1-id = module.network.example_public_subnet1_id
  example-public-subnet2-id = module.network.example_public_subnet2_id
  example-cluster           = module.container.example-cluster
  example-tg                = module.lb.example-tg
}

module "container" {
  source      = "./container"
  example-tg  = module.lb.example-tg
  example-alb = module.lb.example-alb
}

module "cache" {
    source = "./cache"
    example_redis_sg = module.sg.example-redis-sg
    example_private_subnet1_id = module.network.example_private_subnet1_id
    example_private_subnet2_id = module.network.example_private_subnet2_id
}

module "rds" {
  source = "./rds"
  example-public-subnet1-id = module.network.example_public_subnet1_id
  example-public-subnet2-id = module.network.example_public_subnet2_id
  example-rds-sg = module.sg.example-rds-sg
}

module "domain" {
  source      = "./domain"
  example-elb = module.lb.example-alb
}
data "aws_availability_zones" "availability_zones" {
  state = "available"
}

resource "aws_rds_cluster" "example_postgresql" {
  cluster_identifier = "example-postgresql"
  engine             = data.aws_rds_engine_version.example_engine_version.engine
  # engine_mode = "default"
  engine_version         = data.aws_rds_engine_version.example_engine_version.version
  availability_zones     = [data.aws_availability_zones.availability_zones.names[0], data.aws_availability_zones.availability_zones.names[1]]
  database_name          = "example"
  master_username        = "foo"
  master_password        = "bar"
  vpc_security_group_ids = [var.example_rds_sg]
  db_subnet_group_name   = aws_db_subnet_group.example_subnet_group.name
}

data "aws_rds_engine_version" "example_engine_version" {
  engine      = var.engine
  version     = var.engine_version
  include_all = true
}

resource "aws_db_subnet_group" "example_subnet_group" {
  name       = "example-subnet-group"
  subnet_ids = [var.example_public_subnet1_id, var.example_public_subnet2_id]
  tags = {
    Name = "example-subnet-group"
  }
  tags_all = {
    Name = "example-subnet-group"
  }
}
resource "aws_rds_cluster" "example-postgresql" {
    cluster_identifier = "example-postgresql"
    engine = "aurora-postgresql"
    # engine_mode = "default"
    engine_version = data.aws_rds_engine_version.example-engine-version.version
    availability_zones = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
    database_name = "example"
    master_username = "foo"
    master_password = "bar"
    vpc_security_group_ids = [var.example-rds-sg]
    db_subnet_group_name = aws_db_subnet_group.example-subnet-group.name
}

data "aws_rds_engine_version" "example-engine-version" {
    engine      = "aurora-postgresql"
    version     = "15.4"
    include_all = true
}

resource "aws_db_subnet_group" "example-subnet-group" {
    name = "example-subnet-group"
    subnet_ids = [var.example-public-subnet1-id, var.example-public-subnet2-id]
    tags = {
        Name = "example-subnet-group"
    }
    tags_all = {
        Name = "example-subnet-group"
    }
}
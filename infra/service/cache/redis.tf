variable "service_region" {
  default = "ap-northeast-2a"
}

resource "aws_elasticache_cluster" "example_cluster" {
  auto_minor_version_upgrade = "false"
  availability_zone          = var.service_region
  cluster_id                 = "example-cluster"
  ip_discovery               = "ipv4"
  network_type               = "ipv4"
  replication_group_id       = aws_elasticache_replication_group.example_replication_group.replication_group_id

  tags = {
    Name = "example-cache"
  }

  tags_all = {
    Name = "example-cache"
  }

  transit_encryption_enabled = "false"
}

resource "aws_elasticache_replication_group" "example_replication_group" {
  at_rest_encryption_enabled = "false"
  auto_minor_version_upgrade = "false"
  automatic_failover_enabled = "false"
  data_tiering_enabled       = "false"
  description                = "example-cache"
  engine                     = "redis"
  engine_version             = "7.1"
  ip_discovery               = "ipv4"

  log_delivery_configuration {
    destination      = "example-log"
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  log_delivery_configuration {
    destination      = "example-log"
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  maintenance_window = "mon:09:00-mon:10:00"
  multi_az_enabled   = "false"
  network_type       = "ipv4"
  node_type          = "cache.t3.small"
  # num_cache_clusters       = "1"
  num_node_groups          = "1"
  parameter_group_name     = "default.redis7"
  port                     = "6379"
  replicas_per_node_group  = "0"
  replication_group_id     = "example-cache"
  security_group_ids       = [var.example_redis_sg]
  snapshot_retention_limit = "0"
  snapshot_window          = "06:00-07:00"
  subnet_group_name        = aws_elasticache_subnet_group.example_subnet_group.name
  user_group_ids           = []
  timeouts {

  }

  tags = {
    Name = "example-cache"
  }

  tags_all = {
    Name = "example-cache"
  }

  transit_encryption_enabled = "false"
}

resource "aws_elasticache_subnet_group" "example_subnet_group" {
  description = " "
  name        = "example-subnet-group"
  subnet_ids  = [var.example_private_subnet1_id, var.example_private_subnet2_id]
}


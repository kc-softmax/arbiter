resource "aws_elasticache_replication_group" "redis_replication_group" {
  auto_minor_version_upgrade = "false"
  automatic_failover_enabled = "false"
  data_tiering_enabled       = "false"
  description                = "${var.service_name}-redis"
  engine                     = var.engine
  engine_version             = var.engine_version
  ip_discovery               = "ipv4"

  log_delivery_configuration {
    destination      = "${var.service_name}-redis-log"
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  log_delivery_configuration {
    destination      = "${var.service_name}-redis-log"
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  maintenance_window = "mon:09:00-mon:10:00"
  multi_az_enabled   = "false"
  network_type       = "ipv4"
  node_type          = var.cache_node_type
  num_cache_clusters = "1"
  # num_node_groups          = "1"
  parameter_group_name     = var.parameter_group_name
  port                     = 6379
  replicas_per_node_group  = "0"
  replication_group_id     = "${var.service_name}-redis"
  security_group_ids       = [var.redis_sg_id]
  snapshot_retention_limit = "0"
  snapshot_window          = "06:00-07:00"
  subnet_group_name        = aws_elasticache_subnet_group.redis_subnet_group.name
  user_group_ids           = []
  timeouts {

  }

  tags = {
    Name = "${var.service_name}-cache"
  }

  tags_all = {
    Name = "${var.service_name}-cache"
  }

  transit_encryption_enabled = "false"
}

resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  description = "redis subnet group"
  name        = "redis-subnet-group"
  subnet_ids  = [var.private_subnet1_id, var.private_subnet2_id]
}


variable "log_group" {
  default = "/ecs/Example"
}

resource "aws_ecs_cluster" "example-ecs-cluster" {
  name = "Example"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "example-task-definition" {
  family                   = "Example"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  cpu                      = 128
  memory                   = 256
  task_role_arn            = "arn:aws:iam::669354009400:role/ecsTaskExecutionRole"
  execution_role_arn       = "arn:aws:iam::669354009400:role/ecsTaskExecutionRole"
  container_definitions = jsonencode(
    [
      {
        name      = "example-service"
        image     = "nginx:latest"
        cpu       = 128
        memory    = 256
        essential = true
        portMappings = [
          {
            containerPort = 80
            hostPort      = 0
          }
        ]
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-create-group  = "true"
            awslogs-group         = "${var.log_group}"
            awslogs-region        = "ap-northeast-2"
            awslogs-stream-prefix = "ecs"
          }
          secretOptions = []
        }
      }
    ]
  )
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}

resource "aws_ecs_service" "example-ecs-service" {
  name                 = "example-ecs-service"
  launch_type          = "EC2"
  cluster              = aws_ecs_cluster.example-ecs-cluster.id
  iam_role             = "arn:aws:iam::669354009400:role/ecsServiceRole"
  task_definition      = aws_ecs_task_definition.example-task-definition.arn
  desired_count        = 2
  force_new_deployment = true

  load_balancer {
    target_group_arn = var.example-tg.arn
    container_name   = "example-service"
    container_port   = 80
  }

  ordered_placement_strategy {
    type  = "spread"
    field = "instanceId"
  }
  #   placement_constraints {
  #     type       = "memberOf"
  #     expression = "attribute:ecs.availability-zone in [ap-northeast-2a, ap-northeast-2b, ap-northeast-2c]"
  #   }
}

# resource "aws_cloudwatch_log_group" "example-logs" {
#     name = var.log_group
#     retention_in_days = 30
# }

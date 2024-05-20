resource "aws_ecs_cluster" "ecs_cluster" {
  name = var.service_name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "task_definition" {
  family                   = var.service_name
  requires_compatibilities = [var.launch_type]
  network_mode             = "bridge"
  cpu                      = 256
  memory                   = 512
  task_role_arn            = var.task_exec_role_arn
  execution_role_arn       = var.task_exec_role_arn
  container_definitions = jsonencode(
    [
      {
        name      = "${var.service_name}-service"
        image     = "${var.image_url}:latest"
        cpu       = 256
        memory    = 512
        essential = true
        portMappings = [
          {
            containerPort = 9991
            hostPort      = 0
          }
        ]
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-create-group  = "true"
            awslogs-group         = "/ecs/${var.service_name}"
            awslogs-region        = "${var.region}"
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

resource "aws_ecs_service" "ecs_service" {
  name                 = "${var.service_name}-ecs-service"
  launch_type          = var.launch_type
  cluster              = aws_ecs_cluster.ecs_cluster.id
  iam_role             = var.iam_role
  task_definition      = aws_ecs_task_definition.task_definition.arn
  desired_count        = 1
  force_new_deployment = true

  load_balancer {
    target_group_arn = var.ec2_tg.arn
    container_name   = "${var.service_name}-service"
    container_port   = 9991
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

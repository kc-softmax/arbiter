resource "aws_alb_target_group" "example-tg" {
  name     = "example-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.example-vpc

  health_check {
    interval            = 30
    path                = "/"
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }

  tags = { Name = "Example ALB Target Group" }
}

resource "aws_alb" "example-alb" {
  name            = "alb-example"
  internal        = false
  security_groups = ["${var.example-sg}"]
  subnets = [
    "${var.example-public-subnet1-id}",
    "${var.example-public-subnet2-id}"
  ]

  # access_logs {
  #     bucket  = "${aws_s3_bucket.alb.id}"
  #     prefix  = "frontend-alb"
  #     enabled = true
  # }

  tags = {
    Name = "example-alb"
  }


  lifecycle { create_before_destroy = true }
}

resource "aws_alb_listener" "https" {
  load_balancer_arn = aws_alb.example-alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = "arn:aws:acm:ap-northeast-2:669354009400:certificate/65d3f071-0472-406d-9b41-05b771e3a39e"

  default_action {
    target_group_arn = aws_alb_target_group.example-tg.arn
    type             = "forward"
  }

}

data "aws_acm_certificate" "certificate" {
  domain = var.zone_name
}

resource "aws_alb_target_group" "ec2_tg" {
  name     = "${var.service_name}-ec2-tg"
  port     = 9991
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    interval            = 30
    path                = "/docs"
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }

  tags = { Name = "Example ALB Target Group" }
}

resource "aws_alb" "alb" {
  name            = "${var.service_name}-alb"
  internal        = false
  security_groups = ["${var.alb_sg_id}"]
  subnets = [
    "${var.public_subnet1_id}",
    "${var.public_subnet2_id}"
  ]

  # access_logs {
  #     bucket  = "${aws_s3_bucket.alb.id}"
  #     prefix  = "frontend-alb"
  #     enabled = true
  # }

  tags = {
    Name = "${var.service_name}-alb"
  }


  lifecycle { create_before_destroy = true }
}

resource "aws_alb_listener" "https" {
  load_balancer_arn = aws_alb.alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = data.aws_acm_certificate.certificate.arn

  default_action {
    target_group_arn = aws_alb_target_group.ec2_tg.arn
    type             = "forward"
  }

}

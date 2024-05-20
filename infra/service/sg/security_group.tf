data "http" "myip" {
  url = "https://ipv4.icanhazip.com"
}

resource "aws_security_group" "alb_sg" {
  vpc_id      = var.vpc_id
  description = "${var.service_name}-alb-sg"

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = "0"
    protocol    = "-1"
    self        = "false"
    to_port     = "0"
  }

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    description = "http"
    from_port   = "80"
    protocol    = "tcp"
    self        = "false"
    to_port     = "80"
  }

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    description = "https"
    from_port   = "443"
    protocol    = "tcp"
    self        = "false"
    to_port     = "443"
  }

  tags = {
    Name = "${var.service_name}-alb-sg"
  }
  tags_all = {
    Name = "${var.service_name}-alb-sg"
  }
}

resource "aws_security_group" "ec2_sg" {
  vpc_id      = var.vpc_id
  description = "${var.service_name}-ec2-sg"

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = "0"
    protocol    = "-1"
    self        = "false"
    to_port     = "0"
  }

  ingress {
    cidr_blocks = ["${chomp(data.http.myip.response_body)}/32"]
    description = "myip"
    from_port   = "22"
    protocol    = "tcp"
    self        = "false"
    to_port     = "22"
  }

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    description = "http"
    from_port   = "9991"
    protocol    = "tcp"
    self        = "false"
    to_port     = "9991"
  }

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    description = "https"
    from_port   = "443"
    protocol    = "tcp"
    self        = "false"
    to_port     = "443"
  }

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    description = "ecs container port"
    from_port   = "1000"
    protocol    = "tcp"
    self        = "false"
    to_port     = "65535"
  }

  tags = {
    Name = "${var.service_name}-ec2-sg"
  }
  tags_all = {
    Name = "${var.service_name}-ec2-sg"
  }
}

resource "aws_security_group" "redis_sg" {
  vpc_id      = var.vpc_id
  description = "${var.service_name}-redis-sg"

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = "0"
    protocol    = "-1"
    self        = "false"
    to_port     = "0"
  }

  ingress {
    cidr_blocks = ["10.0.0.0/8"]
    description = "redis"
    from_port   = "6379"
    protocol    = "tcp"
    self        = "false"
    to_port     = "6379"
  }

  tags = {
    Name = "${var.service_name}-redis-sg"
  }
  tags_all = {
    Name = "${var.service_name}-redis-sg"
  }
}

resource "aws_security_group" "rds_sg" {
  vpc_id      = var.vpc_id
  description = "${var.service_name}-rds-sg"

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = "0"
    protocol    = "-1"
    self        = "false"
    to_port     = "0"
  }

  ingress {
    cidr_blocks = ["0.0.0.0/8"]
    description = "postgres"
    from_port   = "5432"
    protocol    = "tcp"
    self        = "false"
    to_port     = "5432"
  }

  tags = {
    Name = "${var.service_name}-rds-sg"
  }
  tags_all = {
    Name = "${var.service_name}-rds-sg"
  }
}
data "http" "myip" {
  url = "https://ipv4.icanhazip.com"
}

resource "aws_security_group" "example-ec2-sg" {
  vpc_id      = var.example_vpc_id
  description = "example-sg"

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

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    description = "ecs container port"
    from_port   = "1000"
    protocol    = "tcp"
    self        = "false"
    to_port     = "65535"
  }

  tags = {
    Name = "example-sg"
  }
  tags_all = {
    Name = "example-sg"
  }
}

resource "aws_security_group" "example-redis-sg" {
  vpc_id      = var.example_vpc_id
  description = "example-redis-sg"

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
    Name = "example-redis-sg"
  }
  tags_all = {
    Name = "example-redis-sg"
  }
}

resource "aws_security_group" "example-rds-sg" {
  vpc_id      = var.example_vpc_id
  description = "example-rds-sg"

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
    Name = "example-rds-sg"
  }
  tags_all = {
    Name = "example-rds-sg"
  }
}
# resource "tls_private_key" "test_key" {
#   algorithm = "RSA"
#   rsa_bits  = 4096
# }

# resource "aws_key_pair" "test_keypair" {
#     key_name   = "example-keypair"
#     public_key = tls_private_key.test_key.public_key_openssh

#     provisioner "local-exec" { # Create a "myKey.pem" to your computer!!
#         command = "echo '${tls_private_key.test_key.private_key_pem}' > ./myKey.pem"
#     }
# }

# data "aws_ec2_instance_type" "example-type" {
#     instance_type = "t3.small"
# }

# resource "aws_instance" "example-ec2" {
#   launch_template {

#   }
#   ami = "ami-0032724dd60a24c31"
#   instance_type = data.aws_ec2_instance_type.example-type.instance_type
#   iam_instance_profile = "ecsInstanceRole"
#   associate_public_ip_address = true
#   subnet_id = var.example-public-subnet1-id
#   # key_name = aws_key_pair.test_keypair.key_name
#   key_name = "kc-softmax-ap-norheast-2-211220"
#   vpc_security_group_ids = [var.example-sg-id]
#   # user_data = templatefile("compute/init.tpl", {
#   #   example_cluster_name = var.example-cluster.name
#   # })
#   # user_data = <<-EOF
#   #   #!/bin/bash
#   #   # Amazon Linux 2 AMI
#   #   # 도커 충돌 방지

#   #   amazon-linux-extras disable docker

#   #   # 추가 리포지토리 설치 활성화(도커도 설치 됨)
#   #   amazon-linux-extras install -y ecs

#   #   # 도커 서비스 실행
#   #   service docker start

#   #   # (선택사항) 위와 같이 띄워놓은 ECS 클러스터가 있다면 아래 파일 추가
#   #   echo "ECS_CLUSTER=${var.example-cluster.name}" | tee -a /etc/ecs/ecs.config
#   # EOF

#   # remote 머신에서 ssh로 ubunut 계정으로 머신에 접근, option (inline, script, scripts)
#   provisioner "remote-exec" {
#     inline = [
#       "sudo amazon-linux-extras disable docker",
#       "sudo amazon-linux-extras install -y ecs",
#       "sudo service docker start",
#       "echo ECS_CLUSTER=${var.example-cluster.name} | sudo tee -a /etc/ecs/ecs.config",
#       "sudo service ecs stop",
#       "sudo service ecs start"
#     ]

#     connection {
#       type = "ssh"
#       user = "ec2-user"
#       host = self.public_ip
#       private_key = file("~/.ssh/kc-softmax-ap-norheast-2-211220.pem")
#     }
#   }

#   tags = {
#     Name = "example-ec2"
#   }
#   tags_all = {
#     Name = "example-ec2"
#   }

#   depends_on = [ var.example-cluster ]
# }

resource "aws_launch_configuration" "ec2_launch_configuration" {
  name                        = "${var.service_name}-ec2-launch-configuration"
  image_id                    = var.image_id
  instance_type               = var.instance_type
  iam_instance_profile        = "ecsInstanceRole"
  associate_public_ip_address = true
  key_name                    = var.key_pair
  ebs_block_device {
    device_name = "/dev/sda1"
    volume_type = "gp2"
    volume_size = 20
  }
  security_groups = [var.ec2_sg_id]
  user_data       = <<-EOF
    #!/bin/bash
    # Amazon Linux 2 AMI
    # 도커 충돌 방지

    amazon-linux-extras disable docker

    # 추가 리포지토리 설치 활성화(도커도 설치 됨)
    amazon-linux-extras install -y ecs

    # 도커 서비스 실행
    service docker start

    # (선택사항) 위와 같이 띄워놓은 ECS 클러스터가 있다면 아래 파일 추가
    echo "ECS_CLUSTER=${var.cluster.name}" | tee -a /etc/ecs/ecs.config

    service ecs stop
    # service ecs start
    systemctl enable --now --no-block ecs
  EOF

  depends_on = [var.cluster]
}

resource "aws_autoscaling_group" "example_ag" {
  # 초기 크기
  desired_capacity     = 1
  min_size             = 1
  max_size             = 1
  launch_configuration = aws_launch_configuration.ec2_launch_configuration.name
  vpc_zone_identifier  = [var.public_subnet1_id, var.public_subnet1_id]
  target_group_arns    = [var.ec2_tg.arn]
  instance_maintenance_policy {
    min_healthy_percentage = 60
    max_healthy_percentage = 100
  }

  depends_on = [var.ec2_tg]
}

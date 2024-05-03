#!/bin/bash
# Amazon Linux 2 AMI
# 도커 충돌 방지

amazon-linux-extras disable docker

# 추가 리포지토리 설치 활성화(도커도 설치 됨)
amazon-linux-extras install -y ecs

# 도커 서비스 실행
service docker start

# (선택사항) 위와 같이 띄워놓은 ECS 클러스터가 있다면 아래 파일 추가
echo "ECS_CLUSTER=${example_cluster_name}" | tee -a /etc/ecs/ecs.config

# ecs service 실행
sudo service ecs stop
systemctl enable --now --no-block ecs

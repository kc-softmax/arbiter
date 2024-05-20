
# 필수항목은 cidr이지만, 나머지 항목들은 다음과 같이 설정하여 불편함을 없애도록 한다
resource "aws_vpc" "vpc" {
  assign_generated_ipv6_cidr_block     = "false"
  cidr_block                           = var.vpc_cidr_block
  enable_dns_hostnames                 = "true"
  enable_dns_support                   = "true"
  enable_network_address_usage_metrics = "false"
  instance_tenancy                     = "default"

  tags = {
    Name = "${var.service_name}-vpc"
  }

  tags_all = {
    Name = "${var.service_name}-vpc"
  }
}
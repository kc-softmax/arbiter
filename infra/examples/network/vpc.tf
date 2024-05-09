
# 필수항목은 cidr이지만, 나머지 항목들은 다음과 같이 설정하여 불편함을 없애도록 한다
resource "aws_vpc" "tutorial-vpc" {
  assign_generated_ipv6_cidr_block     = "false"
  cidr_block                           = "${var.vpc_cidr_block}/${var.vpc_subnet_mask}"
  enable_dns_hostnames                 = "true"
  enable_dns_support                   = "true"
  enable_network_address_usage_metrics = "false"
  instance_tenancy                     = "default"

  tags = {
    Name = "tutorial-vpc"
  }

  tags_all = {
    Name = "tutorial-vpc"
  }
}
# 서브넷은 HA(High Availablity)를 위해 2개씩 생성한다
resource "aws_subnet" "example_public_subnet1" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = var.public_subnet1_cidr_block
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2a"

  tags = {
    Name = "example-public-subnet1"
  }

  tags_all = {
    Name = "example-public-subnet1"
  }

  vpc_id = aws_vpc.example_vpc.id
}

resource "aws_subnet" "example_public_subnet2" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = var.public_subnet2_cidr_block
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2b"

  tags = {
    Name = "example-public-subnet2"
  }

  tags_all = {
    Name = "example-public-subnet2"
  }

  vpc_id = aws_vpc.example_vpc.id
}

resource "aws_subnet" "example_private_subnet1" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = var.private_subnet1_cidr_block
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2a"

  tags = {
    Name = "example-private-subnet1"
  }

  tags_all = {
    Name = "example-private-subnet1"
  }

  vpc_id = aws_vpc.example_vpc.id
}

resource "aws_subnet" "example_private_subnet2" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = var.private_subnet2_cidr_block
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2b"

  tags = {
    Name = "example-private-subnet2"
  }

  tags_all = {
    Name = "example-private-subnet2"
  }

  vpc_id = aws_vpc.example_vpc.id
}

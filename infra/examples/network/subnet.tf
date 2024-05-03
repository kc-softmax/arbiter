# 서브넷은 HA(High Availablity)를 위해 2개씩 생성한다
resource "aws_subnet" "tutorial-public-subnet1" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = "10.10.0.0/20"
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2a"

  tags = {
    Name = "tutorial-public-subnet1"
  }

  tags_all = {
    Name = "tutorial-public-subnet1"
  }

  vpc_id = aws_vpc.tutorial-vpc.id
}

resource "aws_subnet" "tutorial-public-subnet2" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = "10.10.16.0/20"
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2b"

  tags = {
    Name = "tutorial-public-subnet2"
  }

  tags_all = {
    Name = "tutorial-public-subnet2"
  }

  vpc_id = aws_vpc.tutorial-vpc.id
}

resource "aws_subnet" "tutorial-private-subnet1" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = "10.10.128.0/20"
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2a"

  tags = {
    Name = "tutorial-private-subnet1"
  }

  tags_all = {
    Name = "tutorial-private-subnet1"
  }

  vpc_id = aws_vpc.tutorial-vpc.id
}

resource "aws_subnet" "tutorial-private-subnet2" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = "10.10.144.0/20"
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = "ap-northeast-2b"

  tags = {
    Name = "tutorial-private-subnet2"
  }

  tags_all = {
    Name = "tutorial-private-subnet2"
  }

  vpc_id = aws_vpc.tutorial-vpc.id
}

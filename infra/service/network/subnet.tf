data "aws_availability_zones" "availability_zones" {
  state = "available"
}

# 서브넷은 HA(High Availablity)를 위해 2개씩 생성한다
resource "aws_subnet" "public_subnet1" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = cidrsubnet(var.vpc_cidr_block, 4, 0)
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = data.aws_availability_zones.availability_zones.names[0]

  tags = {
    Name = "public-subnet1"
  }

  tags_all = {
    Name = "public-subnet1"
  }

  vpc_id = aws_vpc.vpc.id
}

resource "aws_subnet" "public_subnet2" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = cidrsubnet(var.vpc_cidr_block, 4, 1)
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = data.aws_availability_zones.availability_zones.names[1]

  tags = {
    Name = "${var.service_name}-public-subnet2"
  }

  tags_all = {
    Name = "${var.service_name}-public-subnet2"
  }

  vpc_id = aws_vpc.vpc.id
}

resource "aws_subnet" "private_subnet1" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = cidrsubnet(var.vpc_cidr_block, 4, 8)
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = data.aws_availability_zones.availability_zones.names[0]

  tags = {
    Name = "${var.service_name}-private-subnet1"
  }

  tags_all = {
    Name = "${var.service_name}-private-subnet1"
  }

  vpc_id = aws_vpc.vpc.id
}

resource "aws_subnet" "private_subnet2" {
  assign_ipv6_address_on_creation                = "false"
  cidr_block                                     = cidrsubnet(var.vpc_cidr_block, 4, 9)
  enable_dns64                                   = "false"
  enable_resource_name_dns_a_record_on_launch    = "false"
  enable_resource_name_dns_aaaa_record_on_launch = "false"
  ipv6_native                                    = "false"
  map_public_ip_on_launch                        = "false"
  private_dns_hostname_type_on_launch            = "ip-name"
  availability_zone                              = data.aws_availability_zones.availability_zones.names[1]

  tags = {
    Name = "${var.service_name}-private-subnet2"
  }

  tags_all = {
    Name = "${var.service_name}-private-subnet2"
  }

  vpc_id = aws_vpc.vpc.id
}

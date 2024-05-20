resource "aws_internet_gateway" "internet_gateway" {
  vpc_id = aws_vpc.vpc.id
  tags = {
    Name = "${var.service_name}-ig"
  }
  tags_all = {
    Name = "${var.service_name}-ig"
  }
}
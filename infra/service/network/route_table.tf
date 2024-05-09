
resource "aws_route_table" "example_public_route_table" {
  vpc_id = aws_vpc.example_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.example_ig.id
  }
  tags = {
    Name = "example-public-route-table"
  }
  tags_all = {
    Name = "example-public-route-table"
  }
}

resource "aws_route_table_association" "aws-public_route_table_association1" {
  subnet_id      = aws_subnet.example_public_subnet1.id
  route_table_id = aws_route_table.example_public_route_table.id
}

resource "aws_route_table_association" "aws_public_route_table_association2" {
  subnet_id      = aws_subnet.example_public_subnet2.id
  route_table_id = aws_route_table.example_public_route_table.id
}

resource "aws_route_table" "example_private_route_table" {
  vpc_id = aws_vpc.example_vpc.id
  # route {
  #     cidr_block = "0.0.0.0/0"
  #     gateway_id = aws_internet_gateway.example-ig.id
  # }
  tags = {
    Name = "example-private-route-table"
  }
  tags_all = {
    Name = "example-private-route-table"
  }
}

resource "aws_route_table_association" "aws_private_route_table_association1" {
  subnet_id      = aws_subnet.example_private_subnet1.id
  route_table_id = aws_route_table.example_private_route_table.id
}

resource "aws_route_table_association" "aws_private_route_table_association2" {
  subnet_id      = aws_subnet.example_private_subnet2.id
  route_table_id = aws_route_table.example_private_route_table.id
}

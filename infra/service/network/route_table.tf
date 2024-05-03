
resource "aws_route_table" "example-public-route-table" {
  vpc_id = aws_vpc.example-vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.example-ig.id
  }
  tags = {
    Name = "example-public-route-table"
  }
  tags_all = {
    Name = "example-public-route-table"
  }
}

resource "aws_route_table_association" "aws-public-route-table-association1" {
  subnet_id      = aws_subnet.example-public-subnet1.id
  route_table_id = aws_route_table.example-public-route-table.id
}

resource "aws_route_table_association" "aws-public-route-table-association2" {
  subnet_id      = aws_subnet.example-public-subnet2.id
  route_table_id = aws_route_table.example-public-route-table.id
}

resource "aws_route_table" "example-private-route-table" {
  vpc_id = aws_vpc.example-vpc.id
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

resource "aws_route_table_association" "aws-private-route-table-association1" {
  subnet_id      = aws_subnet.example-private-subnet1.id
  route_table_id = aws_route_table.example-private-route-table.id
}

resource "aws_route_table_association" "aws-private-route-table-association2" {
  subnet_id      = aws_subnet.example-private-subnet2.id
  route_table_id = aws_route_table.example-private-route-table.id
}

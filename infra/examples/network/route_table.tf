
resource "aws_route_table" "tutorial-public-route-table" {
  vpc_id = aws_vpc.tutorial-vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.tutorial-ig.id
  }
  tags = {
    Name = "tutorial-public-route-table"
  }
  tags_all = {
    Name = "tutorial-public-route-table"
  }
}

resource "aws_route_table_association" "tutorial-public-route-table-association1" {
  subnet_id      = aws_subnet.tutorial-public-subnet1.id
  route_table_id = aws_route_table.tutorial-public-route-table.id
}

resource "aws_route_table_association" "tutorial-public-route-table-association2" {
  subnet_id      = aws_subnet.tutorial-public-subnet2.id
  route_table_id = aws_route_table.tutorial-public-route-table.id
}

resource "aws_route_table" "tutorial-private-route-table" {
  vpc_id = aws_vpc.tutorial-vpc.id
  # route {
  #     cidr_block = "0.0.0.0/0"
  #     gateway_id = aws_internet_gateway.example-ig.id
  # }
  tags = {
    Name = "tutorial-private-route-table"
  }
  tags_all = {
    Name = "tutorial-private-route-table"
  }
}

resource "aws_route_table_association" "tutorial-private-route-table-association1" {
  subnet_id      = aws_subnet.tutorial-private-subnet1.id
  route_table_id = aws_route_table.tutorial-private-route-table.id
}

resource "aws_route_table_association" "tutorial-prviate-route-table-association2" {
  subnet_id      = aws_subnet.tutorial-private-subnet2.id
  route_table_id = aws_route_table.tutorial-private-route-table.id
}

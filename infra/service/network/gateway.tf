resource "aws_internet_gateway" "example-ig" {
  vpc_id = aws_vpc.example-vpc.id
  tags = {
    Name = "example-ig"
  }
  tags_all = {
    Name = "example-ig"
  }
}
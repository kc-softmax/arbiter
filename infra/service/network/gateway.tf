resource "aws_internet_gateway" "example_ig" {
  vpc_id = aws_vpc.example_vpc.id
  tags = {
    Name = "example-ig"
  }
  tags_all = {
    Name = "example-ig"
  }
}
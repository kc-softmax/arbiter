resource "aws_internet_gateway" "tutorial-ig" {
  vpc_id = aws_vpc.tutorial-vpc.id
  tags = {
    Name = "tutorial-ig"
  }
  tags_all = {
    Name = "tutorial-ig"
  }
}
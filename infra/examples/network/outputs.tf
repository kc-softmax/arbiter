# 다른 모듈에서 사용하는 값들을 작성한다
output "tutorial_vpc_id" {
  value = aws_vpc.tutorial-vpc.id
}

output "tutorial_public_subnet1_id" {
  value = aws_subnet.tutorial-public-subnet1.id
}

output "tutorial_public_subnet2_id" {
  value = aws_subnet.tutorial-public-subnet2.id
}

output "tutorial_private_subnet1_id" {
  value = aws_subnet.tutorial-private-subnet1.id
}

output "tutorial_private_subnet2_id" {
  value = aws_subnet.tutorial-private-subnet2.id
}

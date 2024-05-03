# 다른 모듈에서 사용하는 값들을 작성한다
output "example_vpc_id" {
  value = aws_vpc.example-vpc.id
}

output "example_public_subnet1_id" {
  value = aws_subnet.example-public-subnet1.id
}

output "example_public_subnet2_id" {
  value = aws_subnet.example-public-subnet2.id
}

output "example_private_subnet1_id" {
  value = aws_subnet.example-private-subnet1.id
}

output "example_private_subnet2_id" {
  value = aws_subnet.example-private-subnet2.id
}

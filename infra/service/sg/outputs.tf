output "example-sg" {
  value = aws_security_group.example-ec2-sg.id
}

output "example-redis-sg" {
  value = aws_security_group.example-redis-sg.id
}

output "example-rds-sg" {
  value = aws_security_group.example-rds-sg.id
}

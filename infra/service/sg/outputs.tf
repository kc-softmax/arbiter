output "example_sg" {
  value = aws_security_group.example_ec2_sg.id
}

output "example_redis_sg" {
  value = aws_security_group.example_redis_sg.id
}

output "example_rds_sg" {
  value = aws_security_group.example_rds_sg.id
}

output "ec2_tg" {
  value = aws_alb_target_group.ec2_tg
}
output "alb" {
  value = aws_alb.alb
}

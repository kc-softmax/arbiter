output "example-cluster-id" {
  value = aws_ecs_cluster.example-ecs-cluster.name
}
output "example-cluster" {
  value = aws_ecs_cluster.example-ecs-cluster
}
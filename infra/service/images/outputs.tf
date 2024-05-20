output "image_url" {
  value = aws_ecr_repository.ecr_repository.repository_url
}
output "repo_name" {
  value = aws_ecr_repository.ecr_repository.name
}

output "image_uri" {
  value = aws_ecr_repository.example_repository.repository_url
}
output "repo_name" {
  value = aws_ecr_repository.example_repository.name
}

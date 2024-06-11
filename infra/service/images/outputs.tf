output "service_image_url_map" {
  value = { for ecr_repo in values(aws_ecr_repository.ecr_repositorys).* : ecr_repo.tags.Name => ecr_repo.repository_url }
}
output "arbiter_image_url" {
  value = aws_ecr_repository.arbiter_ecr_repositorys.repository_url
}
output "repo_name_list" {
  value = values(aws_ecr_repository.ecr_repositorys).*.name
}

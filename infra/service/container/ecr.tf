# resource "aws_ecr_repository" "example-repository" {
#   name                 = "example-repository"
#   image_tag_mutability = "MUTABLE"

#   image_scanning_configuration {
#     scan_on_push = true
#   }
# }

# data "aws_ecr_image" "example-image" {
#   repository_name = aws_ecr_repository.example-repository.name
#   image_tag       = "latest"
# }

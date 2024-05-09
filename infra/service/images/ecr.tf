resource "aws_ecr_repository" "example_repository" {
  name                 = "example-repository"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
  force_delete = true
}

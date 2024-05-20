resource "aws_ecr_repository" "ecr_repository" {
  name                 = "${var.service_name}-repository"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
  force_delete = true
}

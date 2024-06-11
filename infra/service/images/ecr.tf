resource "aws_ecr_repository" "ecr_repositorys" {
  for_each             = var.service_list
  name                 = "${each.value}-repository"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
  force_delete = true
  tags = {
    Name = each.value
  }
  tags_all = {
    Name = each.value
  }
}

resource "aws_ecr_repository" "arbiter_ecr_repositorys" {
  name                 = "${var.service_name}-repository"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
  force_delete = true
  tags = {
    Name = var.service_name
  }
  tags_all = {
    Name = var.service_name
  }
}

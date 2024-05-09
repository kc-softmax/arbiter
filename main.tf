module "infra" {
  source   = "./infra"
  key_name = "infra"
}

terraform {
  # You can manage tfstate with S3(default is local storage)
  backend "s3" {
    bucket  = "fourbarracks-tfstate-seoul"
    key     = "resource/terraform.fstate"
    region  = "ap-northeast-2"
    profile = "example"
  }
  required_providers {
    aws = {
      version = "~> 5.43.0"
    }
  }
}

output "rds_endpoint" {
  value = ""
}
output "redis_endpoint" {
  value = module.infra.service.cache.endpoint
}
output "images" {
  value = module.infra.service.images.repo_name
}
output "domain" {
  value = "https://${module.infra.service.domain.domain}/docs"
}

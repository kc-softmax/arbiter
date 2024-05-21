<!-- ### 개발용 환경 변수 설정 방법

`.local.sample.env` 파일을 참고하여 `.local.env` 파일을 만든다.

### pytest 실행 방법

```bash
## 프로젝트 루트 디렉토리에서
## 전체 테스트(test_*.py) 실행
$ pytest
## 특정 폴더
$ pytest tests/auth/
## 특정 파일
$ pytest tests/auth/test_service.py
## 특정 class
$  pytest tests/auth/test_service.py::TestUserService
## 특정 fuction
$  pytest tests/auth/test_service. py::TestUserService::test_register_user_by_device_id
## print 문 출력
$ pytest -s
``` -->
# Arbiter for your competitive multiplayer games

## Arbiter
1. 아비터의 전반적인 소개
2. 아비터의 key features: 장점, 사용해야하는 이유
3. 시작할 수 있도록 도움되는 설명

Why Arbiter

The key features:
- **Stream**:
- **Authenticated**:
- **Dedicated**:
- **Seamless**:

**Command Line**
```shell
arbiter init
arbiter start # (아래의 태스크들을 하나로 묶어야 할지...)
arbiter db # (start background)
arbiter stream # (start background)
# docker compose로 묶어서 실행
arbiter build --target={aws, local...}
# 실행 순서
# 1. 사용 계획(init, plan)
# 2. "Are you sure you want to deploy it?" y/N
# 3. create network, security group
# 4. create cache(redis) for Broker
# 5. get endpoint(redis, (Optional)rds)
# 6. App image push(ECR)
# 7. Create Cluster(LB, Container, Compute, Domain)
# 8. get app domain
```

## IaC(Infrastructure as Code) for deploying your service
### Your service need to deploy in cloude system for playing with user. This code handle AWS resource and writen basic resource for deploying service. If you want to other resource, you can add by referencing document and README.
- [Terraform Script based AWS](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Import Cloud Resource Guide using Terraformer](https://github.com/GoogleCloudPlatform/terraformer/blob/master/docs/aws.md)

**The key features are**:
- **Infrastructure as Code (IaC)**:
You can manage infra as code when you using terraform. Through this, developer and system manager can track changed resource and manage version and infra easily.
- **Provider Ecosystem**:
Terraform compatible with AWS, Microsoft Azure, Google Cloud. User can manage almost skill stack and service using terraform.
- **Modular Design**:
Terraform module can recycle, share the code and manage infra more efficiently. Module can share in terraform community, user can appply already verified infra pattern.
- **Change Automation and Orchestration**:
Terraform manage changed infra by plan and apply. Through this, predict what will change before update, plan stable deployment by solve dependancy automatically before real apply.
- **State Management**:
Terraform manage present state of infra by tracking. User understand about present state of infra by state file and help maintain consistent envrioment accross team.

### Prepare
**You need authentication for accessing cloud resource. First, create console account and add policy**

**MAC**
```shell
# aws cli
brew install awscli
brew install terraform
# (Optional)
brew install tfenv
```

**Linux(ubuntu)**
```shell
# aws cli
sudo apt-get update -y
sudo apt-get install awscli
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

**Window**
- [awscli](https://docs.aws.amazon.com/ko_kr/cli/latest/userguide/getting-started-install.html)
- [terraform](https://developer.hashicorp.com/terraform/install#windows)

**aws configure**
```shell
aws configure --profile name
# input your aws_access_key_id
# input your aws_secret_access_key
# input default region name like ap-northeast-2(Seoul), us-west-1(North California)
# input default output format

# (Optional) terraform virtual env
tfenv install specific version
tfenv use version

# you can check terraform version
terraform version
```

### main.tf script
- **main.tf include child module and terraform state**
```hcl
module "infra" {
  source   = "git::https://github.com/kc-softmax/arbiter-server.git//infra?ref=develop"

  service_name = "" # input your service name
  cidr = "" # input your network class like 10.10.0.0/16
  region = "" # input your deployment region
  instance_type = "" # input type of instance
  cache_node_type = "" # input type of cache node
  zone_name = "" # you have to register the domain
  record_name = "" # input host name
  key_pair = "" # input specific key name you made
}

terraform {
  # You can manage tfstate with S3(default is local storage)
  # backend "s3" {
  #   bucket  = "" # input bucket name you made
  #   key     = "" # input key/file name
  #   region  = "" # input bucket region name you made
  #   profile = "" # input aws configure profile
  # }
  required_providers {
    aws = {
      version = "~> 5.43.0"
    }
  }
}

### please do not change below output field ###
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
  value = "https://${module.infra.service.domain.domain_name}/docs"
}
```

### Deploy
- **CLI**: You can deploy the cloud resource using below cli.
```shell
# You have to execute init when you add tf file
terraform init

# You can check resource state compare with cloud(add, change, destroy state)
terraform plan

# You can deploy all of cloud resource(please check changed resource using plan before apply)
terraform apply

# (Optional) You can deploy specific cloud resource(please check changed resource using plan before apply)
terraform apply -target={module....}

# This command will remove all of cloud resource
terraform destroy 

# (Optional) You can remove specific cloud resource
terraform destroy -target={module...}
```

**service와 examples**
```shell
# only include VPC service
terraform apply -target=module.infra.module.examples

# include All of necessary service
terraform apply -target=module.infra.module.service
```

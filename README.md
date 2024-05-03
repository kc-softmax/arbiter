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

## IaC(Infrastructure as Code) for deploying your service
### Your service need to deploy in cloude system for playing with user. This code handle AWS resource and writen basic resource for deploying service. If you want to other resource, you can add by referencing document and README.
- [Terraform Script based AWS](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Import Cloud Resource Guide using Terraformer](https://github.com/GoogleCloudPlatform/terraformer/blob/master/docs/aws.md)

**The key features are**:
- **Infrastructure as Code (IaC)**:
Terraform을 사용하면 인프라를 코드로 관리할 수 있습니다. 이를 통해 개발자와 시스템 관리자가 인프라를 보다 쉽게 관리하고, 버전 관리하며, 변경사항을 추적할 수 있습니다.
- **Provider Ecosystem**:
Terraform은 AWS, Microsoft Azure, Google Cloud 등을 포함한 다양한 프로바이더와 호환됩니다. 사용자는 이를 통해 거의 모든 기술 스택과 서비스를 자동으로 관리할 수 있습니다.
- **Modular Design**:
Terraform 모듈을 사용하면 코드를 재사용하고, 공유하며, 더욱 효율적인 인프라 관리가 가능합니다. 모듈은 Terraform 커뮤니티 내에서 공유될 수 있어, 사용자는 이미 검증된 인프라 패턴을 손쉽게 적용할 수 있습니다.
- **Change Automation and Orchestration**:
Terraform은 계획과 적용의 두 단계로 인프라 변경 사항을 관리합니다. 이를 통해 변경 전에 무엇이 변경될지 예측하고, 실제 적용 전에 자동으로 종속성을 해결하며 안정적인 배포를 도모합니다.
- **State Management**:
Terraform은 인프라의 현재 상태를 추적하여 관리합니다. 이 상태 파일은 사용자가 인프라의 현재 상태를 이해하고, 팀 간에 일관된 환경을 유지하도록 돕습니다.
- **Security and Compliance**:
Terraform 코드를 사용하여 보안 기준과 규정 준수 요구사항을 코딩할 수 있습니다. 이는 인프라 배포 과정에서 보안과 규정을 자동으로 적용할 수 있게 돕습니다.

### Prepare
**AWS 클라우드에 배포할 때 필요한 패키지들에 대한 설명.
클라우드 리소스에 접근하기 위해 클라우드 계정과 권한이 필요합니다. 콘솔 계정을 생성하고 필요한 권한을 추가해주세요. 필요한 리소스들은 terraform을 통해 배포될 것입니다.**

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

### Configure your environment
AWS의 profile을 등록하고 terraform의 버전을 확인해주세요

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

### Example(main.tf script)
root 경로에서 하위 모듈들을 인식하여 구조화
```hcl
module "service" {
  source   = "./infra"
  key_name = "infra"
}

terraform {
  You can manage tfstate with S3(default is local storage)
  Manage tfstate using S3(First, you have to create Bucket) 
  backend "s3" {
    bucket  = "Bucket Name" like "example"
    key     = "specific Key path in Bucket" like "/example.tfstate"
    region  = "specific region" like "ap-northeast-2" "us-west-1"
    profile = "your profile name created aws configure --profile name"
  }
  required_providers {
    aws = {
      version = "~> major.minor.patch" like 5.43.0
    }
  }
}
```

### Deploy
**hcl 스크립트를 작성했다면 아래의 명령어를 사용하여 클라우드에 배포 할 수 있습니다.
클라우드 배포에 필요한 명령어로 자주 사용되는 명령어입니다.**
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

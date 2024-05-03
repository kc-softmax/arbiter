# Terraform structure

## HashiCorp Script
```hcl
# Define variable for using string or int value of resource
variable "name" {
  default=""
}

# Define output value for exporting to root module
output "name" {
  value=""
}

# Define exist cloud data format
# Here is example about AMI(Amazon Machine Image)
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm*"]
  }
}

# Define cloud resource for deploying
# You have to check essential key
resource "aws_instance" "name" {
  instance_type = "t3.micro"
}
```

## Module
- Import folder using source key
- This can share variable between module

## Example Service
You have to know the billing of cloud price. Example module exist for checking deployment of cloud resource(It does not charge price). If you deploy example module, you can see vpc and subnet resource in AWS console. Then, you can try deploy the real cloud service using other module.
- **example**:
This module include vpc and subnet. This module was make for checking deployment of cloud resource
- **service**:
This module include all of essential cloud resource like instance, domain, container. You must go over necessary resource for your service
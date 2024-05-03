# Service deployment

This service module include basic resource for service. You can communicate with your server(not local) when you deploy cloud resource and code.

- **compute**:
This module include like EC2 instance. We provide container instance to use docker image.
- **container**:
This module include ECS(container image, container service). It interact with container instance.
- **domain**:
This module include Route53(hosting your service). Before You have to buy domain in registrar.
- **lb**:
This module include ELB(ALB, NLB, GLB). ELB will distribute the request to target(EC2, ECS).
- **network**:
This module include VPC, subnet, internet gateway, route table resource. This resource is very important in cloud system. If you want to use compute instance or database, you must assign subnet area. Then, you can access in instance when you assign public subnet. If you want to use private subnet for security, you have to create NAT and bastion server to access
- **rds**:
This module include RDS(MySQL, MSSQL, PostgreSQL ...). 
- **cache**:
This module include ElastiCache(Redis, MemCached).
- **sg**:
This module include Security Group.

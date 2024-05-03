# Network

## VPC
```text
어떤 네트워크 대역을 사용할 것인지를 정의한다
cidr_block = 가능한 block 10.0.0.0/9(이상), 172.16.0.0-172.31.0.0/16(이상), 192.168.0.0-192.168.255.0/24(이상)
나머지 설정은 참고하여 필요에 따라 true false를 지정한다
```

## Subnet
```text
VPC의 범위에 해당하는 네트워크 대역을 지정하며 서비스는 subnet의 범위내의 private ip를 부여받고 같은 vpc내에서 서로 통신할 수 있다.
cidr_block = vpc에서 지정한 대역의 범위내에서 선언한다
availability_zone = 문서에서 참고하여 리전별로 지원가능한 가용영역을 찾아서 지정한다.
```

## Route Table
```text
서브넷에서 subnet과 외부간 경로를 인식할 수 있는 중요한 역할을 한다
Route Table
vpc_id = 생성한 vpc의 id를 참조한다.
route {
    peering, NAT, Internet Gateway 등 다양한 타겟을 지정하여 통신할 수 있다.
}
```

## Gateway
```text
NAT, Internet Gateway로 network의 관문 역할을 한다.
vpc_id = 생성한 vpc의 id를 참조한다.
```

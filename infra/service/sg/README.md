# SG

## Security Group
```text
인터페이스의 inbound와 outbound에 대한 규칙을 지정한다.
vpc_id = 생성한 vpc의 id를 참조한다.
ingress {
    inbound로 진입하는 대상의 ip와 protocol을 지정하여 허용한다
}
egress {
    outbound로 클라우드에서 내보내는 통신으로 전체 허용한다
}
```

# Load Balancer

## Application Load Balancer
```text
Load Balancer의 Target Group
Group 내에 여러 개의 Container Instance를 등록하여 Load Balancer가 분산 처리할 수 있도록한다.
port = 서비스의 host or bridge port를 입력한다.
vpc_id = Container Instance와 동일한 VPC
health_check {
    등록된 Container Instance는 일정 주기로 정상적인 상태인지 확인되어야 한다.
}

Load Balancer
서비스 진입 전 트래픽의 라우팅을 결정한다.
internal = true이면 내부 false이면 외부 접근을 허용한다.
security_groups = security_group에서 inbound의 port에 따라 접속을 차단한다.
subnets = 다중화를 지향하기 때문에 여러 가용영역을 지정한다.

Load Balancer Listener
Load Balancer의 수신받을 포트와 Target Group을 연결하는 역할
load_balancer_arn = 생성한 load balancer의 arn을 참조한다.
port = 수신받을 port를 지정한다.
protocol = HTTP, HTTPS를 지정한다.
default_action {
    여러개의 타겟 그룹을 지정하여 서비스 API 혹은 가중치에 따라 라우팅 할 수 있다.
}
```
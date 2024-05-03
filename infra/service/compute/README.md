# Resource

## Launch Templates
```text
Container Instance를 신규로 띄울 때 반복적으로 발생하는 작업을 줄일 수 있다.
자주 실행되거나 내부 구성 값이 바뀌지 않는다면 template으로 미리 정의하고 빠르게 배포할 수 있도록 구성하였다.
주요 키워드는
image = aws의 market place에서 원하는 이미지의 id값을 기입한다(container instance로 해당 이미지를 선택하였다)
key = console에서 생성한 pem 키의 이름을 기입한다
instance_type = 서비스의 사용량에 따라 버스트(t, m type), 연산 처리(c type), 메모리 기반(r type) 혹은 다른 케이스를 참고하여 기입한다

나머지 설정은 필요에 따라 추가한다
```
## AutoScaling
```text
사전에 정의된 launch template에 의해 서비스의 사용량에 따라 Container Instance가 조정된다
desired_capacity = 초기 시작 개수
min_size = 최소 실행 개수
max_size = 최대 실행 개수
launch_configuration = 미리 정의된 launch template
vpc_zone_identifier = 서버의 다중화에 대한 지원하는 영역 기입
instance_maintenance_policy {
    min_healthy_percentage = 최소 건강 상태(아래로 내려가면 min_size만큼 개수가 줄어든다)
    max_healthy_percentage = 최대 건강 상태(도달하면 최대 max_size만큼 개수가 늘어난다)
}
```

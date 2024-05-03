# container

## ECR
```text
private, public의 repository와 repository 내부에 image가 버전별로 관리된다.
사용자마다 달라질 수 있어서 관리 요소인지 판단이 필요하다.
```

## ECS
```text
모니터링 및 서비스관리를 위한 ECS cluster
EC2, Fargate, 외부 인스턴스를 가질 수 있다.

서비스에 필요한 작업 정의
requires_compatibilities = EC2 or Fargate
network_mode = 주체가되는 host와 바인딩으로 생성되는 bridge, 클라우드 vpc가 있다.
cpu = 인스턴스의 크기에 따라 작은 값을 입력
memory = 인스턴스의 크기에 따라 작은 값을 입력
container_definitions {
    태스크에 여러 컨테이너가 등록될 수 있다.
    image의 주소와 cpu, memory는 상위에서 정의한 값의 일정량 분배된 값을 입력하다.
}
runtime_platform {
    system(window, linux), architecture(arm, amd)를 설정한다.
}

서비스
위의 생성된 클러스터와 태스크에 기반하여 서비스를 배포한다
launch_type = EC2 or Fargate(task의 requires_compatibilities, cluster의 환경과 일치시킨다)
cluster = 정의된 클러스터의 아이디를 참조한다.
iam_role = 서비스를 실행할 때 필요한 정책이 포함된 arn을 입력한다.
task_definition = 정의된 task의 arn을 참조한다.
desired_count = 시작 서비스의 수를 지정한다
force_new_deployment = 최초 배포 이후에 신규 배포시 서비스가 바로 반영되기를 원한다면 true, 아니면 false로 한다
load_balancer {
    미리 정의된 target group의 arn과 container name, port를 지정하여 연결시킨다
}
ordered_placement_strategy {
    서비스의 사용량 혹은 성격에 따라 균등, 메모리 기반, 특정 인스턴스로 설정 할 수 있다(현재는 균등)
}
```

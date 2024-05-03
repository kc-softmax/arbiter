# domain

## Route53
```text
Route53 또한 Certificate Manager와 관련해서 수동으로 관리하는 것이 필요하기 때문에 호스팅 기능만 추가하였다.
도메인을 의미하는 zone
name = 구매한 도메인을 입력
private_zone = internal로 사용한다면 true, internet이라면 false로 입력

도메인의 서브도메인을 의미하는 record
zone_id = 위에 생성한 zone의 참조 id
name = 서브도메인을 포함한 주소를 입력
type = A이면 ipv4, AAAA이면 ipv6, CNAME이면 타 도메인 주소로 라우팅 할 수 있다
alias {
    클라우드의 배포된 서비스 중 하나를 입력한다.
    ELB, EC2의 public ip(수동으로 인증서 등록하여 https), CloudFront의 dns_name과 zone_id(region)을 참조한다 
}
```
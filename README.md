### 개발용 환경 변수 설정 방법

`.local.sample.env` 파일을 참고하여 `.local.env` 파일을 만든다.

### postgresql docker 실행
```bash
## 실행
docker run -itd -p 5432:5432 --restart always -e POSTGRES_USER=arbiter -e POSTGRES_PASSWORD=arbiter -e POSTGRES_DB=arbiter -v postgres-data:/var/lib/postgresql/data --name arbiter-db postgres:15.3-alpine
## 데이터 초기화 할려면 volume 삭제 후 실행
docker rm -f arbiter-db
docker volume rm -f postgres-data

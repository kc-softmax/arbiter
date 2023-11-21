### 개발용 환경 변수 설정 방법

`.local.sample.env` 파일을 참고하여 `.local.env` 파일을 만든다.

### postgresql docker 실행
```bash
docker run -itd -p 5432:5432 --restart always -e POSTGRES_USER=arbiter -e POSTGRES_PASSWORD=arbiter -e POSTGRES_DB=arbiter -v postgres-data:/var/lib/postgresql/data postgres:15.3-alpine
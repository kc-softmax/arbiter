### 개발용 환경 변수 설정 방법

`src` 패키지 안에 `.local.sample.env` 파일을 참고하여 `.local.env` 파일을 만든다.



### pytest 실행 방법
```bash
## 프로젝트 루트 디렉토리에서
## 전체 테스트(test_*.py) 실행
$ pytest
## 특정 폴더
$ pytest tests/auth/
## 특정 파일
$ pytest tests/auth/test_service.py
## 특정 class
$  pytest tests/auth/test_service.py::TestUserService
## 특정 fuction
$  pytest tests/auth/test_service. py::TestUserService::test_register_user_by_device_id
## print 문 출력
$ pytest -s
```



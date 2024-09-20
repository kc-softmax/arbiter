from arbiter import ArbiterRunner, ArbiterApp
from arbiter.gateway import ArbiterGatewayService
from tests.service import TestService, TestException

# 서비스가 시작할때, gateway intra server에 task model을 등록 
# 서비스가 실행되어질때, gateway에 task model을 등록 <바뀌는점>
app = ArbiterApp(
    name='test',
    arbiter_host='localhost',
    arbiter_port=6379,
    config={
        'warp_in_timeout': 10,
        'system_timeout': 30,
        'service_timeout': 10,
        'service_health_check_interval': 4,
        'service_health_check_func_clock': 0.1,
        'service_retry_count': 3,
        'service_pending_timeout': 10,
    }
)
app.add_service(
    ArbiterGatewayService())
# app.add_service(
#     ArbiterGatewayService())
app.add_service(TestException())
app.add_service(TestService())

# broker의 config은 app의 config로 설정
# 나머지 설정은 생성하면서 설정

if __name__ == '__main__':
    ArbiterRunner.run(app)

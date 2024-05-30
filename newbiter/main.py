import asyncio

class Arbiter:
    
    def __init__(self) -> None:
        # 서비스 운용에 사용되는 데이터베이스
        self.operation_db = ""
        # 메시지 브로커
        self.broker = ""
        # 구 아비타(웹서버 서비스)
        self.web_server_service = ""

    # cli 등에서 실행
    def start(self):
        # 기본으로 실행되어야 할 서비스들 시작
        self.start_default_service()
        # 시각 기록 task
        asyncio.run(self.record_running_time())
        # 서비스 구동 확인 task, delay 필요
        asyncio.run(self.health_check())

    # cli 등에서 실행
    def start_service(self):
        pass

    # cli 등에서 실행
    def stop_service(self):
        pass

    def start_default_service(self):
        # config 에서 구 arbiter main app 경로를 가져와 import
        # import path
        self.web_server_service = ""
        # 새로운 프로세스에서 실행?
        new_process.run(self.web_server_service.start())
        self.operation_db.add_service("web server 시작함")

    async def record_running_time(self):
        async for message in self.broker.listen():
            # message에는 어떤 서비스인지 담겨 있음
            service = message.service
            # 해당 서비스의 시간 업데이트
            self.operation_db.update_time(service)

    def health_check(self):
        services = self.operation_db.get_services()
        for service in services:
            time = self.operation_db.get_last_time_of_service(service)
            if not self.is_running_service(time):
                self.operation_db.remove_service(service)
                self.broker.broadcast_service_stop(service)
                # reset?
            
    
    def is_running_service(self, time) -> bool:
        base_time = 0
        # 현재 시간
        now = 1
        # 현재 시간과의 차이를 계산 하여 기준 시간보다 작아야 구동중
        return now - time < base_time
    


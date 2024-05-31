import asyncio
import anyio
import watchfiles

class Arbiter:
    
    def __init__(self) -> None:
        # 서비스 운용에 사용되는 데이터베이스
        self.operation_db = ""
        # 메시지 브로커
        self.broker = ""
        # 구 아비타(웹서버 서비스)
        self.web_server_service = ""


    # cli 등에서 실행
    async def start(self, app_path: str, host: str, port: str, reload: bool):
        # reload 값에 따라
        # watchfiles로 실행할지, 그냥 실행할지 결정해야함
        if reload:
            await watchfiles.arun_process('arbiter_server', target=self.start_web_server, args=(app_path, host, port, reload))
        else:
            uvicorn_command = f"uvicorn {app_path} --host {host} --port {port}"
            await asyncio.create_subprocess_shell(
            uvicorn_command,
            shell=True,
        ) 
        
        # web_server = self.start_web_server(web_server_run_command)
        # print("hohohohoh")
        # await web_server

        # 시각 기록 task
        # asyncio.run(self.record_running_time())
        # 서비스 구동 확인 task, delay 필요
        # asyncio.run(self.health_check())

    # cli 등에서 실행
    def start_service(self):
        pass

    # cli 등에서 실행
    def stop_service(self):
        pass

    def start_web_server(self, app_path: str, host: str, port: int, reload: bool):
        # process로 실행이 된다.
        import uvicorn
        import os
        uvicorn.run(app=app_path, host=host, app_dir=os.getcwd())

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
    


 # TODO
 # watch file에서 파일 변경 감지 및 재실행

arbiter = Arbiter()
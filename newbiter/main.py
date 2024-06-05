import asyncio
import sys
import atexit
import signal
import os
import importlib
import uvicorn
from newbiter.abstract_sercvice import AbstractService
from newbiter.utils import find_python_files_in_path, get_running_command 


class Arbiter:
    
    def __init__(self) -> None:
        # 서비스 운용에 사용되는 데이터베이스
        self.operation_db = ""
        # 메시지 브로커
        self.broker = ""
        # 구 아비타(웹서버 서비스)
        self.web_server_service = ""
        # 등록된 서비스들
        self.registered_services: list[type[AbstractService]] = []
        # 서비스 pdis
        self.pids: dict[str, int] = {}

    def init_broker(self):
        print('init broker!')

    # cli 등에서 실행
    async def start(self, app_path: str, host: str, port: int, reload: bool):  
        # exit 이벤트에 cleanup 함수를 등록
        atexit.register(self.cleanup)

        # 1. init broker
        self.init_broker()

        # 2. register service
        self.register_services()

        # 3. start services(background)
        service_running_tasks = []
        for service in self.registered_services:
            service_running_tasks.append(asyncio.create_task(self.start_service(service.__name__)))
        # 메인 프로세스(newbiter.main.start())가 종료되지 않고 계속 잡아두기 위한 방법
        # 추후 web server(fast api)등으로 잡고 있다면 필요 없음
        for task in service_running_tasks:
            await task

    def register_services(self):
        python_files_in_root = find_python_files_in_path()        
        # 서비스 파일(root아래)들을 import
        for python_file in python_files_in_root:
            importlib.import_module(python_file)
        # import 되었으므로 AbstractService의 subclasses로 접근 가능
        for service in AbstractService.__subclasses__():
            self.registered_services.append(service)

    # cli 등에서 실행 가능
    async def start_service(self, service_name: str):
        # 중복 실행 막기
        # ...
        
        # 실행
        # 서비스 클래스 이름(eg)AchivementService)으로 서비스 찾기
        service = next((service for service in self.registered_services if service.__name__ == service_name), None)
        if service is None:
            raise Exception('실행하려는 서비스가 등록되지 않았습니다.')
        command = get_running_command(service.__module__, service_name)
        proc = await asyncio.create_subprocess_shell(
            f'{sys.executable} -c "{command}"',
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        self.pids[service_name] = proc.pid
        _, error = await proc.communicate()
        print(error.decode())
        
    # cli 등에서 실행 가능
    def stop_service(self, service_name: str):
        pid = self.pids.pop(service_name)
        os.kill(pid, signal.SIGTERM)        

    # NOTE: SIGNKILL은 잡을 수 없다.
    def cleanup(self):
        print("Cleaning up resources...")

    # def start_web_server(self, app_path: str, host: str, port: int):
    #     uvicorn.run(app=app_path, host=host, port=int(port), app_dir=os.getcwd())

    # async def record_running_time(self):
    # def health_check(self):    
    # def is_running_service(self, time) -> bool:
    
arbiter = Arbiter()
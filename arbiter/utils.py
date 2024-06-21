import importlib
from pathlib import Path


# NOTE _new_service로 찾는 것은 루트 경로 내에서 서비스 파일을 찾기 위한 임시 조치

def find_python_files_in_path(dir_path: str = './'):
    service_file_name_suffix = '_service'
    current_path = Path(dir_path)
    python_files = [str(p).split('.py')[0] for p in current_path.iterdir()
                    if p.is_file() and p.suffix == '.py' and str(p).split('.py')[0].find(service_file_name_suffix) > 0]
    return python_files


def find_registered_services(python_files_in_root: list[str], abstract_service: type):
    registered_services = []
    # 서비스 파일(root아래)들을 import
    for python_file in python_files_in_root:
        importlib.import_module(python_file)
    # import 되었으므로 AbstractService의 subclasses로 접근 가능
    for service in abstract_service.__subclasses__():
        registered_services.append(service)
    return registered_services


def get_running_command(module_name: str, service_name: str):
    # init에서 파라미터를 받으면 안됨..
    # call에서 실행할 경우 run 없어도됨
    return f'import asyncio; from {module_name} import {service_name}; asyncio.run({service_name}.launch());'


def get_all_subclasses(cls) -> list[type]:
    subclasses = cls.__subclasses__()
    all_subclasses = list(subclasses)
    for subclass in subclasses:
        all_subclasses.extend(get_all_subclasses(subclass))
    return all_subclasses

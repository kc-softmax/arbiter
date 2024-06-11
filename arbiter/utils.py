from pathlib import Path

# NOTE _new_service로 찾는 것은 루트 경로 내에서 서비스 파일을 찾기 위한 임시 조치


def find_python_files_in_path(dir_path: str = './'):
    service_file_name_suffix = '_service'
    current_path = Path(dir_path)
    python_files = [str(p).split('.py')[0] for p in current_path.iterdir()
                    if p.is_file() and p.suffix == '.py' and str(p).split('.py')[0].find(service_file_name_suffix) > 0]
    return python_files


def get_running_command(module_name: str, service_name: str):
    # init에서 파라미터를 받으면 안됨..
    # call에서 실행할 경우 run 없어도됨
    return f'import asyncio; from {module_name} import {service_name}; asyncio.run({service_name}.launch());'

import os
import configparser
import platform
import re
import pickle
import signal
import socket
import types
import inspect
import time
import asyncio
import importlib
import psutil
from asyncio.subprocess import Process
from datetime import datetime
from pydantic import BaseModel, create_model
from warnings import warn
from inspect import Parameter
from pathlib import Path
from typing import (
    Union, 
    get_origin,
    get_args,
    Any,
    List,
    Awaitable,
    Callable,
    Optional
)

async def check_redis_running(
    host: str = "localhost",
    port: int = 6379,
    password: str = None,
) -> bool:
    from redis.asyncio import ConnectionPool, Redis, ConnectionError
    try:
        if password:
            redis_url = f"redis://:{password}@{host}:{port}/"
        else:
            redis_url = f"redis://{host}:{port}/"

        async_redis_connection_pool = ConnectionPool.from_url(
            redis_url,
            socket_timeout=5,
        )
        redis = Redis(connection_pool=async_redis_connection_pool)
        await redis.ping()
        await redis.aclose()
        await async_redis_connection_pool.disconnect()
        return True
    except ConnectionError:
        return False

def read_config(config_file: str):
    """
    Reads configuration from an INI file.
    """
    file_path = os.path.join(config_file)
    if os.path.exists(file_path):
        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(), allow_no_value=True)
        config.read(file_path)
        return config
    return None

def get_task_queue_name(
    service_name: str,
    task_name: str,
) -> str:
    return f"{to_snake_case(service_name)}_{task_name}"

def get_os():
    system = platform.system()
    if system == "Darwin":
        return "OS X"
    elif system == "Linux":
        return "Linux"
    else:
        return "Other"
    
async def terminate_process(process: Process):
    try:
        kill_signal = signal.SIGTERM
        match get_os():
            case "Linux":
                kill_signal = signal.SIGKILL
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.send_signal(kill_signal)
        parent.send_signal(kill_signal)
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except asyncio.TimeoutError:
            for child in children:
                child.kill()
            parent.kill()
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        print(e)


async def fetch_data_within_timeout(
    timeout: int, 
    fetch_data: Callable[[], Awaitable[List[Any]]], 
    check_condition: Optional[Callable[[List[Any]], bool]] = None,
    sleep_interval: float = 0.5
) -> List[Any]:
    """
    주어진 시간 동안 조건을 검사하고, 마지막으로 조건을 만족하는 데이터를 반환합니다.
    조건이 제공되지 않으면 fetch_data 함수가 데이터를 반환할 때까지 반복합니다.

    :param timeout: 조건을 검사할 최대 시간 (초 단위)
    :param fetch_data: 조건을 만족하는 데이터를 반환하는 비동기 함수
    :param check_condition: 데이터를 기반으로 조건을 검사하는 함수 (선택 사항)
    :param sleep_interval: 각 검사 사이의 대기 시간 (초 단위)
    :return: 조건을 만족하는 데이터 리스트
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        data = await fetch_data()
        # check_condition이 있으면 조건을 검사하고, 없으면 data가 있는지만 검사합니다.
        if check_condition:
            if check_condition(data):
                return data
        else:
            if data:
                return data
        
        await asyncio.sleep(sleep_interval)
    
    raise TimeoutError(f"Timeout in fetching data within {timeout} seconds")

async def get_data_within_timeout(
    timeout: int,
    fetch_data: Callable[[], Awaitable[Any]],
    check_condition: Optional[Callable[[Any], bool]] = None,
    sleep_interval: float = 0.5
) -> Any:
    start_time = time.time()
    while time.time() - start_time < timeout:
        data = await fetch_data()
        if check_condition:
            if check_condition(data):
                return data
        else:
            if data:
                return data
        await asyncio.sleep(sleep_interval)
    

def get_ip_address() -> str:
    """
    현재 서버의 IP 주소를 반환합니다.
    
    :return: 현재 서버의 IP 주소
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
    except Exception as e:
        ip_address = ''
    return ip_address


def get_pickled_data(data: bytes) -> None | Any:
    """
    주어진 바이트 문자열이 피클된 데이터인지 확인합니다.
    
    :param data: 확인할 바이트 문자열
    :return: 피클된 데이터인지 여부 (True/False)
    """
    # 1. 피클의 매직 바이트를 확인합니다.
    if len(data) < 2 or data[0] != 0x80:
        return None

    # 2. 실제 언피클링을 시도하여 유효한지 확인합니다.
    try:
        return pickle.loads(data)
    except (
        pickle.UnpicklingError, 
        EOFError,
        AttributeError,
        ImportError, 
        IndexError,
        TypeError
    ):  
        return None

def get_type_from_type_name(type_name: str, default_type=None) -> type | None:
    type_mapping = {
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'string': str,
        'integer': int,
        'number': float,
        'boolean': bool,
        'datetime': datetime,
        'array': list,
        'object': dict[str, Any],
        'Any': Any,
    }
    return type_mapping.get(type_name, default_type)

def create_model_from_schema(schema: dict) -> BaseModel:
    def handle_object_type(details: dict):
        if 'additionalProperties' in details:
            additional_type = get_type_from_type_name(details['additionalProperties']['type'])
            return dict[str, additional_type]
        else:
            return dict[str, Any]
        
    fields = {}
    for name, details in schema['properties'].items():
        if details.get('format') == 'date-time':
            field_type = datetime
        elif details.get('type') == 'object':
            field_type = handle_object_type(details)
        else:
            field_type = get_type_from_type_name(details.get('type', 'Any'))
        fields[name] = (field_type, ...)
    return create_model(schema['title'], **fields)  

def convert_param(param_type: type, request_param: Any) -> Any:
    if issubclass(param_type, BaseModel):
        return param_type.model_validate(request_param)
    else:
        if param_type == bool:
            # 특별 처리 로직
            return request_param.lower() in ('true', '1', 'yes')
        elif param_type == Any:
            return request_param
        return param_type(request_param)

def parse_request_body(
    request_body: dict[str, Any],
    func_params: dict[str, Parameter],
) -> dict[str, Any]:
    """
        사용자 부터 받은 request_body를 func_params에 맞게 파싱합니다. 
    """
    params = {}
    for param_name, param in func_params.items():
        if param_name not in request_body:
            # 사용자로 부터 받은 request_body에 param_name이 없다면
            if param.default != inspect.Parameter.empty:
                # 기본값이 있는 경우
                params[param_name] = param.default
            elif (
                get_origin(param.annotation) is Union or
                isinstance(param.annotation, types.UnionType)
            ):
                # Union type 이지만 None이 없는 경우
                if type(None) not in get_args(param.annotation):
                    raise ValueError(
                        f"Invalid parameter: {param_name}, {param_name} is required")
                # Optional type
                params[param_name] = get_default_type_value(param)                            
            else:
                raise ValueError(
                    f"Invalid parameter: {param_name}, {param_name} is required"
                )
        else:
            #사용자로 부터 받은 request_body에 param_name이 있다.
            request_param = request_body.pop(param_name, None)
            param_type = param.annotation
            is_list = False
            origin = get_origin(param_type)
            if origin is list or origin is List:
                if not isinstance(request_param, list):
                    raise ValueError(
                        f"Invalid parameter: {param_name}, {param_name} must be a list of {param_type.__name__}")
                param_type = get_args(param_type)[0]
                is_list = True
            try:
                if is_list:
                    params[param_name] = [
                        convert_param(item)
                        for item in request_param]
                else:
                    params[param_name] = convert_param(param_type, request_param)
            except Exception as e:
                print(e)
                raise ValueError(
                    f"Invalid parameter: {param_name}, {e}")
            
    if request_body:
        warn(f"Unexpected parameters: {request_body.keys()}")
    
    return params

def get_default_type_value(param: Parameter) -> any:
    annotation = param.annotation
    if get_origin(annotation) is Union or isinstance(annotation, types.UnionType):
        # Handle Union types
        args = get_args(annotation)
        if type(None) in args:
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                # Recursively get the default value for the non-None type
                return get_default_type_value(Parameter(name=param.name, kind=param.kind, default=param.default, annotation=non_none_args[0]))
            else:
                return None
    elif annotation == str:
        return ""
    elif annotation == int:
        return 0
    elif annotation == float:
        return 0.0
    elif annotation == list:
        return []
    elif annotation == dict:
        return {}
    elif annotation == bool:
        return False
    else:
        return None  # Default value for unspecified types

def extract_annotation(param: Parameter) -> str:
    annotation = param.annotation
    # Optional[int]는 Union[int, None]과 동일합니다.
    if get_origin(annotation) is Union:
        args = get_args(annotation)
        # NoneType이 아닌 첫 번째 타입을 반환합니다.
        if len(args) == 2 and type(None) == args[1]:
            # Optional의 경우
            return f"Optional[{[arg for arg in args if arg is not type(None)][0].__name__}]"
        else:
            union_args = ", ".join(arg.__name__ for arg in args)
            return f"Union[{union_args}]"
    elif hasattr(annotation, "__module__"):
        return f"{annotation.__module__}.{annotation.__name__}"
    else:    
        return annotation.__name__

def to_camel_case(s: str) -> str:
    # 첫 단어는 소문자로 변환
    s = s.lower()
    # 단어를 구분하는 구분자 (공백, 밑줄, 대시)를 찾아서 단어로 분리
    parts = re.split(r'[_\-\s]', s)
    # 첫 번째 단어는 그대로 두고, 나머지 단어는 첫 글자를 대문자로 변환
    camel_case_str = parts[0] + ''.join(word.capitalize() for word in parts[1:])
    return camel_case_str

def to_snake_case(name: str) -> str:
    # Convert CamelCase or PascalCase to snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
# NOTE _new_service로 찾는 것은 루트 경로 내에서 서비스 파일을 찾기 위한 임시 조치


def find_python_files_in_path(dir_path: str = './', from_replica: bool = False):
    def check_file(p) -> bool:
        is_arbiter_service = False
        only_master_service = False
        with open(p, 'r') as file:
            content = file.read()
            if re.search(r'class\s+\w+\(ArbiterWorker\)', content):
                is_arbiter_service = True
            if re.search(r'master_only\s*=\s*True', content):
                only_master_service = True
            if re.search(r'master_only=True', content):
                only_master_service = True
            if re.search(r'master_only\s*=True', content):
                only_master_service = True
            if re.search(r'master_only=/s*True', content):
                only_master_service = True
        if only_master_service:
            return is_arbiter_service and not from_replica
        return is_arbiter_service  

    current_path = Path(dir_path)
    python_files = []
    # Check root directory files
    for p in current_path.iterdir():
        if p.is_file() and p.suffix == '.py':
            if check_file(p):
                python_files.append(str(p).split('.py')[0])

    # Check 'services' directory files
    services_path = current_path / 'services'
    if services_path.exists() and services_path.is_dir():
        for p in services_path.iterdir():
            if p.is_file() and p.suffix == '.py' and p.name != '__init__.py':
                if check_file(p):
                    file_name = str(p).replace('/', '.').split('.py')[0]
                    python_files.append(file_name)

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


def get_all_subclasses(cls) -> list[type]:
    subclasses = cls.__subclasses__()
    all_subclasses = list(subclasses)
    for subclass in subclasses:
        all_subclasses.extend(get_all_subclasses(subclass))
    return all_subclasses

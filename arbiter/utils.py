import os
import json
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
import warnings
import psutil
from collections import abc
from asyncio.subprocess import Process
from datetime import datetime
from pydantic import BaseModel, Field, create_model
from warnings import warn
from inspect import Parameter
from pathlib import Path
from types import NoneType, UnionType
from typing import (
    AsyncGenerator,
    Tuple,
    Union, 
    get_origin,
    get_args,
    Any,
    Dict,
    List,
    Awaitable,
    Callable,
    Optional
)
from arbiter.constants import ALLOWED_TYPES, CONFIG_FILE

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

def is_optional_type(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is Union or isinstance(annotation, UnionType):
        return type(None) in get_args(annotation)
    return False

def get_type_in_optional_type(annotation: Any) -> Any:
    if is_optional_type(annotation):
        args = get_args(annotation)
        return [arg for arg in args if arg is not type(None)][0]
    return annotation

def restore_type(transformed_type: list[Any]) -> Any:
    def get_type(type: Any) -> Any:
        if isinstance(type, dict):
            return parse_json_schema_to_pydantic(type)
            # return create_model_from_schema(type)
        else:
            return get_type_from_type_name(type)
        
    if not transformed_type:
        return None
    elif len(transformed_type) == 1:
        # single type
        return get_type(transformed_type[0])
    elif len(transformed_type) > 1:
        # Union type or List type or Dict type
        type_definition = transformed_type[0]
        if type_definition == 'list' or type_definition == 'tuple':
            return list[restore_type(transformed_type[1:])]
        elif type_definition == 'dict':
            key = transformed_type[1]
            value = transformed_type[2]
            key = restore_type(key) if isinstance(key, list) else get_type(key)
            value = restore_type(value) if isinstance(value, list) else get_type(value)
            return dict[key, value]
        else:
            return Union[tuple(get_type(type) for type in transformed_type)]
    else:
        return Any

def transform_type_from_annotation(annotation: Any) -> list[type]:
    parameter_types = []
    if (
        get_origin(annotation) == AsyncGenerator or 
        get_origin(annotation) == types.AsyncGeneratorType or
        get_origin(annotation) == abc.AsyncGenerator
    ):
        args = get_args(annotation)
        if len(args) > 2:
            raise ValueError(
                f"Invalid return type: {annotation}, expected: AsyncGenerator[Type, None]")
        if args[1] is not NoneType:
            raise ValueError(
                f"Invalid return type: {annotation}, expected: AsyncGenerator[Type, None]")
        parameter_types = [args[0]]
    elif (
        get_origin(annotation) is Union or
        isinstance(annotation, UnionType)
    ):
        parameter_types = get_args(annotation)
    elif (
        get_origin(annotation) is list or
        get_origin(annotation) is tuple or
        get_origin(annotation) is List or
        get_origin(annotation) is Tuple
    ):
        parameters = get_args(annotation)
        parameter_types = [list]
        # TODO MARK 재귀함수로 만들어야 하나?
        for parameter in parameters:
            if (
                get_origin(parameter) is Union or
                isinstance(parameter, UnionType)
            ):
                parameter_types += get_args(parameter)
            else:
                parameter_types.append(parameter)
    elif (
        get_origin(annotation) is dict or
        get_origin(annotation) is Dict
    ):
        if get_origin(annotation):
            args = get_args(annotation)
            if len(args) != 2:
                raise ValueError(
                    f"Invalid return type: {annotation}, expected: dict[Type, Type] or Dict[Type, Type]")
            parameter_types = [dict, args[0], args[1]]
        else:
            parameter_types = [dict, Any, Any]    
    else:
        # check if return type is allowed
        if not (annotation in ALLOWED_TYPES or issubclass(annotation, BaseModel)):
            raise ValueError(f"Invalid response type: {annotation}, allowed types: {ALLOWED_TYPES}")                
        parameter_types = [annotation]
    return parameter_types

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
        'list': list[Any],
        'dict': dict[Any, Any],
        'Any': Any,
    }
    return type_mapping.get(type_name, default_type)

def parse_json_schema_to_pydantic(schema: dict):
    properties = schema.get('properties', {})
    required = schema.get('required', [])
    additional_properties = schema.get('additionalProperties', True)

    # 필드 타입 매핑 함수
    def map_field_type(field_schema: dict):
        field_type = field_schema.get('type')
        title = field_schema.get('title', None)
        default = field_schema.get('default', None)
        format = field_schema.get('format', None)
        if format == 'date-time':
            return datetime, Field(default, title=title)

        if 'anyOf' in field_schema:
            types = [sub_schema['type'] for sub_schema in field_schema['anyOf']]
            if 'null' in types:
                non_null_type = next(t for t in types if t != 'null')
                if non_null_type == 'integer':
                    return Optional[int], Field(default, title=title)
                elif non_null_type == 'string':
                    return Optional[str], Field(default, title=title)
            return Any, Field(default, title=title)

        if 'enum' in field_schema:
            enum_values = field_schema['enum']
            if field_type == 'string':
                return str, Field(default, title=title, description=f"Allowed values: {enum_values}")
            if field_type == 'integer':
                return int, Field(default, title=title, description=f"Allowed values: {enum_values}")
        
        if field_type == 'array':
            item_schema = field_schema.get('items', {})
            item_type, item_field = map_field_type(item_schema)
            return List[item_type], Field(default, title=title)

        if field_type == 'object':
            nested_schema = field_schema
            nested_model = parse_json_schema_to_pydantic(nested_schema)
            return nested_model, Field(default, title=title)

        if field_type == 'integer':
            minimum = field_schema.get('minimum', None)
            maximum = field_schema.get('maximum', None)
            constraints = {}
            if minimum is not None:
                constraints['ge'] = minimum
            if maximum is not None:
                constraints['le'] = maximum
            return int, Field(default, title=title, **constraints)

        if field_type == 'string':
            min_length = field_schema.get('minLength', None)
            max_length = field_schema.get('maxLength', None)
            pattern = field_schema.get('pattern', None)
            constraints = {}
            if min_length is not None:
                constraints['min_length'] = min_length
            if max_length is not None:
                constraints['max_length'] = max_length
            if pattern is not None:
                constraints['regex'] = pattern
            return str, Field(default, title=title, **constraints)

        if field_type == 'boolean':
            return bool, Field(default, title=title)

        return Any, Field(default, title=title)

    # 필드 정의
    fields = {}
    for field_name, field_schema in properties.items():
        field_type, field_info = map_field_type(field_schema)
        if field_name in required:
            fields[field_name] = (field_type, field_info)
        else:
            fields[field_name] = (Optional[field_type], field_info)


    # Pydantic 모델 생성
    model_name = schema.get('title', 'DynamicModel')
    return create_model(model_name, **fields)

# deprecated
# def create_model_from_schema(schema: dict) -> BaseModel:
#     def handle_object_type(details: dict):
#         if 'additionalProperties' in details:
#             additional_type = get_type_from_type_name(details['additionalProperties']['type'])
#             return dict[str, additional_type]
#         else:
#             return dict[str, Any]
        
#     fields = {}
#     for name, details in schema['properties'].items():
#         if details.get('format') == 'date-time':
#             field_type = datetime
#         elif details.get('type') == 'object':
#             field_type = handle_object_type(details)
#         else:
#             field_type = get_type_from_type_name(details.get('type', 'Any'))
#         fields[name] = (field_type, ...)
#     return create_model(schema['title'], **fields)  

def convert_data_to_annotation(data: Any, annotation: Any) -> Any:
    if data is None:
        return None
    valid_annotation = get_type_in_optional_type(annotation)
    origin = get_origin(valid_annotation)

    if origin is list or origin is List:        
        args = get_args(valid_annotation)[0]
        return [convert_data_to_annotation(item, args) for item in data]
    else:
        if issubclass(valid_annotation, BaseModel):
            return valid_annotation.model_validate(data)
        else:
            origin = get_origin(valid_annotation)
            if valid_annotation == Any:
                return data
            if valid_annotation == bool:
                # 특별 처리 로직
                return data.lower() in ('true', '1', 'yes')
            return valid_annotation(data)

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
            if re.search(r'class\s+\w+\(ArbiterServiceWorker\)', content):
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


def get_arbiter_setting(config_file: str) -> tuple[str, bool]:
    """
        os.environ.get('ARBITER_HOME') 등에 대해 고려도 해봐야겠다
        기준은 최초 arbiter를 실행한 시점으로(좋은 방법은 아니기 때문에 다른방법이 생각나면 교체)
        base_path(현재경로)부터 home_path(user 경로)까지 검사한다

        arbiter.setting.ini파일은 현재 경로부터 유저경로까지 탐색하기 때문에 파일을 찾게되면 생성하지 않는다
    """

    arbiter_home = os.environ.get("ARBITER_HOME", os.getcwd())

    home_path = Path(os.path.expanduser("~"))
    base_path = Path(arbiter_home)
    depth_path = base_path
    arbiter_setting = depth_path.joinpath(config_file)
    is_arbiter_setting = False
    while home_path != depth_path:
        if arbiter_setting.exists():
            is_arbiter_setting = True
            break
        depth_path = depth_path.parent
        arbiter_setting = depth_path.joinpath(config_file)

    # arbiter.setting.ini파일을 못찾았기 때문에 현재 실행경로에 생성할 수 있도록 경로를 지정한다
    if not is_arbiter_setting:
        arbiter_setting = base_path.joinpath(config_file)

    return arbiter_setting, is_arbiter_setting

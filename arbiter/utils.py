import re
import types
import inspect
import importlib
from datetime import datetime
from pydantic import BaseModel, create_model
from warnings import warn
from inspect import Parameter
from pathlib import Path
from typing import Union, get_origin, get_args, Any, List

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
        'Any': Any,
    }
    return type_mapping.get(type_name, default_type)

def create_model_from_schema(schema: dict) -> BaseModel:
    fields = {}
    for name, details in schema['properties'].items():
        # datetime 형식의 문자열을 인식하여 datetime 타입으로 변환
        if details.get('format') == 'date-time':
            field_type = datetime
        else:
            field_type = get_type_from_type_name(details['type'])
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


def to_snake_case(name: str) -> str:
    # Convert CamelCase or PascalCase to snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
# NOTE _new_service로 찾는 것은 루트 경로 내에서 서비스 파일을 찾기 위한 임시 조치


def find_python_files_in_path(dir_path: str = './', is_master: bool = False):
    current_path = Path(dir_path)
    python_files = []
    def check_file(p):
        is_arbiter_service = False
        only_master_service = False
        with open(p, 'r') as file:
            content = file.read()
            if re.search(r'class\s+\w+\(RedisService\)', content):
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
            return is_arbiter_service and is_master
        return is_arbiter_service  

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

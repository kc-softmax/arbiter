import re
import importlib
from inspect import Parameter
from pathlib import Path
from typing import Union, get_origin, get_args


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


def find_python_files_in_path(dir_path: str = './'):
    # service_file_name_suffix = '_service'
    current_path = Path(dir_path)
    python_files = [str(p).split('.py')[0] for p in current_path.iterdir()
                    if p.is_file() and p.suffix == '.py']
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

import os
import configparser
import asyncio
import inspect
import subprocess
import importlib
from functools import wraps, partial
from pathlib import Path
from typer import Typer
from enum import StrEnum


class Shortcut(StrEnum):
    SHOW_SERVICE_LIST = "a"
    SHOW_ACTIVE_SERVICES = "r"
    START_SERVICE = "s"
    KILL_SERVICE = "k"
    SHOW_SHORTCUT = "h"
    EXIT = "q"


class Providers(StrEnum):
    AWS = "aws"
    DEV = "dev"
    LOCAL = "local"


class Communication(StrEnum):
    RETURN_OUT = "OUT_ON"
    TERMINAL_OUT = "OUT_OFF"
    RETURN_ERR = "ERR_ON"
    TERMINAL_ERR = "ERR_OFF"


class Commands(StrEnum):
    TERRAFORM_INIT = "terraform init"
    TERRAFORM_PLAN = "terraform plan {var}"
    TERRAFORM_APPLY = "terraform apply {var} -target={module} -auto-approve"
    TERRAFORM_DESTROY = "terraform destroy -auto-approve"
    TERRAFORM_OUTPUT = "terraform output -json"
    PRISMA_PUSH = "prisma db push"
    PRISMA_GENERATE = "prisma generate"


class SupportedModules(StrEnum):
    CACHE = "module.infra.module.service.module.cache"
    COMPUTE = "module.infra.module.service.module.compute"
    CONTAINER = "module.infra.module.service.module.container"
    DOMAIN = "module.infra.module.service.module.domain"
    IMAGES = "module.infra.module.service.module.images"
    LB = "module.infra.module.service.module.lb"
    NETWORK = "module.infra.module.service.module.network"
    RDS = "module.infra.module.service.module.rds"
    SG = "module.infra.module.service.module.sg"


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


def write_config(config: configparser.ConfigParser, config_file: str):
    """
    Reads configuration from an INI file.
    """
    file_path = os.path.join(config_file)
    with open(file_path, "w") as fp:
        config.write(fp)
    return None


def refresh_output(pwd: str = None):
    terraform_refresh_plan = subprocess.Popen(
        args=["terraform plan -refresh-only"],
        shell=True,
        cwd=pwd
    )
    terraform_refresh_plan.wait(86400)
    terraform_refresh_apply = subprocess.Popen(
        args=["terraform apply -refresh-only -auto-approve"],
        shell=True,
        cwd=pwd
    )
    terraform_refresh_apply.wait(86400)


def popen_command(
    command: Commands,
    communication_out: Communication = Communication.TERMINAL_OUT,
    communication_err: Communication = Communication.TERMINAL_ERR,
    pwd: str = None
) -> str | list[str]:
    proc = subprocess.Popen(
        args=[command],
        stdout=subprocess.PIPE if communication_out == Communication.RETURN_OUT else None,
        stderr=subprocess.PIPE if communication_err == Communication.RETURN_ERR else None,
        shell=True,
        cwd=pwd,
    )
    proc.wait(86400)
    # It will return bytes type value when you input Communication.RETURN_OUT
    # It will return None type value when you input Communication.TERMINAL_OUT,
    # you can see output in terminal
    stdout, stderr = proc.communicate()
    if stdout:
        stdout = stdout.decode()
    if stderr:
        stderr = stderr.decode()
    return stdout, stderr


async def check_db_server(drivername: str, username: str, password: str, hostname: str, port: int) -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.engine import URL
    from sqlalchemy.exc import OperationalError
    status = True
    url = URL.create(
        drivername=drivername,
        username=username if username else None,
        password=password if password else None,
        host=hostname if hostname else None,
        port=port if port else None
    )
    engine = create_async_engine(url)
    try:
        conn = await engine.connect()
        await conn.close()
    except OperationalError:
        status = False
    return status


def check_cache_server(url: str) -> bool:
    import redis
    status = True
    try:
        r = redis.StrictRedis(url)
        r.ping()
    except redis.ConnectionError:
        status = False
    return status


def get_command(module: str, name: str):
    return f"python -c 'from {module} import {name}; {name}.run();'"


def find_python_files_in_path(dir_path: str = './'):
    current_path = Path(dir_path)
    python_files = [str(p).split('.py')[0] for p in current_path.iterdir(
    ) if p.is_file() and p.suffix == '.py']
    return python_files


class AsyncTyper(Typer):
    @staticmethod
    def maybe_run_async(decorator, f):
        if inspect.iscoroutinefunction(f):

            @wraps(f)
            def runner(*args, **kwargs):
                return asyncio.run(f(*args, **kwargs))

            decorator(runner)
        else:
            decorator(f)
        return f

    def callback(self, *args, **kwargs):
        decorator = super().callback(*args, **kwargs)
        return partial(self.maybe_run_async, decorator)

    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)
        return partial(self.maybe_run_async, decorator)

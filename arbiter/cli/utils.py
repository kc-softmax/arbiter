import os
import configparser
import asyncio
import inspect
import subprocess
from functools import wraps, partial
from typer import Typer
from enum import StrEnum


class TERRAFORM_COMMAND(StrEnum):
    INIT = "terraform init"
    PLAN = "terraform plan"
    APPLY = "terraform apply -target={module} -auto-approve"
    DESTROY = "terraform destroy"
    OUTPUT = "terraform output -json"


class SUPPORTED_MODULE(StrEnum):
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
        config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
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


def refresh_output(pwd: str):
    terraform_images = subprocess.Popen(
        args=["terraform plan -refresh-only"],
        shell=True,
        cwd=pwd
    )
    terraform_images.wait(86400)
    terraform_images = subprocess.Popen(
        args=["terraform apply -refresh-only -auto-approve"],
        shell=True,
        cwd=pwd
    )
    terraform_images.wait(86400)


def popen_command(command: TERRAFORM_COMMAND, pwd: str, module: str = None) -> str | list[str]:
    match command:
        case TERRAFORM_COMMAND.APPLY:
            res = subprocess.Popen(
                args=[command.format(module=module)],
                stderr=subprocess.PIPE,
                shell=True,
                cwd=pwd,
            )
            res.wait(86400)
            _, stderr = res.communicate()
            return stderr.decode()
        case TERRAFORM_COMMAND.OUTPUT:
            res = subprocess.Popen(
                args=[command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                cwd=pwd,
            )
            res.wait(86400)
            stdout, stderr = res.communicate()
            return stdout.decode(), stderr.decode()
        case _:
            res = subprocess.Popen(
                args=[command],
                stderr=subprocess.PIPE,
                shell=True,
                cwd=pwd,
            )
            res.wait(86400)
            _, stderr = res.communicate()
            return stderr.decode()
        


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
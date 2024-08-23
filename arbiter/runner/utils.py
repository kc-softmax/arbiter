import os
import configparser
import asyncio
import inspect
import subprocess
from functools import wraps, partial
from typer import Typer
from mako.template import Template
from arbiter.constants import PROJECT_NAME, CONFIG_FILE
from enum import Enum


class Providers(Enum):
    AWS = "aws"
    DEV = "dev"
    LOCAL = "local"


class Communication(Enum):
    RETURN_OUT = "RETURN_OUT"
    TERMINAL_OUT = "TERMINAL_OUT"
    RETURN_ERR = "RETURN_ERR"
    TERMINAL_ERR = "TERMINAL_ERR"


class Commands(Enum):
    TERRAFORM_INIT = "terraform init"
    TERRAFORM_PLAN = "terraform plan {var}"
    TERRAFORM_APPLY = "terraform apply {var} -target={module} -auto-approve"
    TERRAFORM_DESTROY = "terraform destroy -auto-approve"
    TERRAFORM_OUTPUT = "terraform output -json"
    PRISMA_PUSH = "prisma db push"
    PRISMA_GENERATE = "prisma generate"


class SupportedModules(Enum):
    CACHE = "module.infra.module.service.module.cache"
    COMPUTE = "module.infra.module.service.module.compute"
    CONTAINER = "module.infra.module.service.module.container"
    DOMAIN = "module.infra.module.service.module.domain"
    IMAGES = "module.infra.module.service.module.images"
    LB = "module.infra.module.service.module.lb"
    NETWORK = "module.infra.module.service.module.network"
    RDS = "module.infra.module.service.module.rds"
    SG = "module.infra.module.service.module.sg"

def write_config(config: configparser.ConfigParser, config_file: str):
    """
    Reads configuration from an INI file.
    """
    file_path = os.path.join(config_file)
    with open(file_path, "w") as fp:
        config.write(fp)
    return None

def create_config(project_path='.'):
    """
    Creates a basic project structure with predefined files and directories.
    :param project_path: Base path where the project will be created
    """
    project_structure = {
        ".": [CONFIG_FILE],
    }
    template_root_path = f'{os.path.abspath(os.path.dirname(__file__))}/templates'
    for directory, files in project_structure.items():
        dir_path = os.path.join(project_path, directory)
        os.makedirs(dir_path, exist_ok=True)

        for file in files:
            file_path = os.path.join(dir_path, file)
            template_path = f'{template_root_path}'
            if str(file).find('.mako') != -1:
                template_file = os.path.join(template_path, file)
                with open(template_file, 'r') as tf:
                    with open(file_path, "w") as of:
                        of.write(tf.read())
            else:
                template_file = os.path.join(template_path, f'{file}.mako')
                with open(template_file, 'r') as tf:
                    template = Template(tf.read())
                    with open(file_path, "w") as of:
                        if template_file.find(CONFIG_FILE) != -1 or template_file.find("env.py") != 1:
                            of.write(template.render(
                                project_name=PROJECT_NAME))
                        else:
                            of.write(template.render())

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
) -> tuple[str, str]:
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
    if isinstance(stdout, bytes):
        stdout = stdout.decode()
    if isinstance(stderr, bytes):
        stderr = stderr.decode()
    return (stdout, stderr)


def check_cache_server(url: str) -> bool:
    import redis
    status = True
    try:
        r = redis.StrictRedis(url)
        r.ping()
    except redis.ConnectionError:
        status = False
    return status


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

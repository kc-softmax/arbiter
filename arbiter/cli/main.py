import os
import typer
import subprocess
import pathlib
import json
from typing import Optional
from typing_extensions import Annotated
from mako.template import Template
from enum import StrEnum

from arbiter.cli import PROJECT_NAME, CONFIG_FILE
from arbiter.cli.commands.database import app as database_app
from arbiter.cli.utils import (
    read_config,
    write_config,
    refresh_output,
    popen_command,
    TERRAFORM_COMMAND,
    SUPPORTED_MODULE,
)

app = typer.Typer()
app.add_typer(database_app, name="db", help="Execute commands for database creation and migration.")


class PROVIDER(StrEnum):
    AWS = "aws"


@app.command()
def init(
    base_path: Optional[str] = typer.Option(".", "--path", "-p", help="The base path where to create the project.")
):
    """
    Creates a basic project structure with predefined files and directories.
    """    
    _create_project_structure(base_path)
    typer.echo(f"Project created successfully.")

@app.command()
def start(
    app_path: Annotated[Optional[str], typer.Argument(..., help="The path to the FastAPI app, e.g., 'myapp.main:app'")] = f"{PROJECT_NAME}.main:arbiterApp",
    host: str = typer.Option(None, "--host", "-h", help="The host of the Arbiter FastAPI app."),
    port: int = typer.Option(None, "--port", "-p", help="The port of the Arbiter FastAPI app."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for code changes.")
):
    """
    Read the config file.
    """
    config = read_config(CONFIG_FILE)
    if (config is None):
        typer.echo("No config file path found. Please run 'init' first.")
        return

    """
    Get the "host" and "port" from config file.
    """
    host = host or config.get("fastapi", "host", fallback=None)
    port = port or config.get("fastapi", "port", fallback=None)
    if (host is None or port is None):
        typer.echo("Set the port and host in 'arbiter.settings.ini' or give them as options.")
        return
        
    """
    Starts the Arbiter FastAPI app using Uvicorn.
    """
    typer.echo("Starting FastAPI app...")
    # Command to run Uvicorn with the FastAPI app
    uvicorn_command = f"uvicorn {app_path} --host {host} --port {port}"
    
    # Add reload option if specified
    if reload:
        uvicorn_command += " --reload"

    # Use subprocess to execute the command
    subprocess.run(uvicorn_command, shell=True)


def _create_project_structure(project_path='.'):
    """
    Creates a basic project structure with predefined files and directories.

    :param project_path: Base path where the project will be created
    """
    project_structure = {
        PROJECT_NAME: ["engine.py", "main.py", "model.py", "repository.py"],
        f"{PROJECT_NAME}/migrations": ["env.py", "README", "script.py.mako"],
        f"{PROJECT_NAME}/migrations/versions": [],
        ".": [CONFIG_FILE],
    }
    template_root_path = f'{os.path.abspath(os.path.dirname(__file__))}/templates'
    for directory, files in project_structure.items():
        dir_path = os.path.join(project_path, directory)
        os.makedirs(dir_path, exist_ok=True)

        for file in files:
            file_path = os.path.join(dir_path, file)
            
            if dir_path.find("migrations") != -1:
                template_path = f'{template_root_path}/alembic'
            elif dir_path.find(PROJECT_NAME) != -1:
                template_path = f'{template_root_path}/arbiter'
            else:
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
                            of.write(template.render(project_name=PROJECT_NAME))
                        else:
                            of.write(template.render())


@app.command()
def build(
    target: Optional[str] = typer.Option("local", "--target", help="Optional deploy to cloud(aws) or local")
):
    package_path = os.path.dirname(os.path.abspath(__file__))
    root_path = pathlib.Path(package_path)
    pwd = str(root_path.parent.parent)
    match target:
        case PROVIDER.AWS:
            # prepare deploy cloud resource
            stderr = popen_command(TERRAFORM_COMMAND.INIT, pwd)
            if stderr:
                print(stderr)
                raise typer.Abort()
            stderr = popen_command(TERRAFORM_COMMAND.PLAN, pwd)
            if stderr:
                print(stderr)
                raise typer.Abort()
            deploy = typer.confirm("Are you sure you want to deploy it?")
            if not deploy:
                raise typer.Abort()

            # 1. deploy network, security group
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.NETWORK)
            if stderr:
                print(stderr)
                raise typer.Abort()
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.SG)
            if stderr:
                print(stderr)
                raise typer.Abort()

            # 2. deploy cache
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.CACHE)
            if stderr:
                print(stderr)
                raise typer.Abort()
            refresh_output(pwd)

            # 3. get endpoint
            stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT, pwd)
            if stderr:
                print(stderr)
                raise typer.Abort()
            output: dict[str, str] = json.loads(stdout)
            if output.get("redis_endpoint"):
                config = read_config("arbiter.setting.ini")
                config.set("cache", "redis.url", output["redis_endpoint"]["value"])
                config.set("database", "port", "443")
                config.set("database", "hostname", "s0.fourbarracks.io")
                write_config(config, "arbiter.setting.ini")
            else:
                stderr = popen_command(TERRAFORM_COMMAND.DESTROY, pwd)
                print(stderr)
                raise typer.Abort()

            # 4. docker(ECR, push image)
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.IMAGES)
            if stderr:
                print(stderr)
                raise typer.Abort()
            refresh_output(pwd)
            stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT, pwd)
            if stderr:
                print(stderr)
                raise typer.Abort()
            output: dict[str, str] = json.loads(stdout)
            if output.get("images"):
                repo_name = output["images"]["value"]
                build_and_push = subprocess.Popen(
                    args=[f"./build_and_push.sh {repo_name} ap-northeast-2 linux/amd64 ./"],
                    shell=True,
                )
                build_and_push.wait(86400)
            
            # 5. deploy service(ECS, Container Instance, ELB, domain)
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.LB)
            if stderr:
                print(stderr)
                raise typer.Abort()
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.CONTAINER)
            if stderr:
                print(stderr)
                raise typer.Abort()
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.COMPUTE)
            if stderr:
                print(stderr)
                raise typer.Abort()
            stderr = popen_command(TERRAFORM_COMMAND.APPLY, pwd, SUPPORTED_MODULE.DOMAIN)
            if stderr:
                print(stderr)
                raise typer.Abort()
            refresh_output(pwd)
            stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT, pwd)
            if stderr:
                print(stderr)
                raise typer.Abort()
            output: dict[str, str] = json.loads(stdout)
            if output.get("domain"):
                domain_name = output["domain"]["value"]
                print(domain_name)
        case _:
            print("not supported provider")


if __name__ == "__main__":
    app()

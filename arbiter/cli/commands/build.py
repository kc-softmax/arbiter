import typer
import os
import pathlib
import json

from arbiter.cli.utils import AsyncTyper
from arbiter.cli.utils import (
    read_config,
    write_config,
    refresh_output,
    popen_command,
    TERRAFORM_COMMAND,
    SUPPORTED_MODULE,
)


app = AsyncTyper()


@app.command(help="build local kubernetes deployment enviroment")
def local():
    typer.echo(typer.style("not supported yet", fg=typer.colors.RED, bold=True))


@app.command(help="build AWS cloud resource for deployment")
def cloud():
    package_path = os.path.dirname(os.path.abspath(__file__))
    root_path = pathlib.Path(package_path)
    pwd = str(root_path.parent.parent)
    try:
        # Usage plan
        stderr = popen_command(TERRAFORM_COMMAND.INIT)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.PLAN)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        deploy = typer.confirm("Are you sure you want to deploy it?")
        if not deploy:
            raise typer.Abort()

        # 1. create network, security group
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.NETWORK)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.SG)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()

        # 2. create cache
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.CACHE)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        refresh_output()

        # 3. get endpoint
        stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        output: dict[str, str] = json.loads(stdout)
        if output.get("redis_endpoint"):
            config = read_config("arbiter.setting.ini")
            config.set("cache", "redis.url", output["redis_endpoint"]["value"])
            config.set("database", "port", "443")
            config.set("database", "hostname", "s0.fourbarracks.io")
            write_config(config, "arbiter.setting.ini")
        else:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()

        # 4. docker(ECR, push image)
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.IMAGES)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        refresh_output()
        stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        output: dict[str, str] = json.loads(stdout)
        if output.get("images"):
            repo_name = output["images"]["value"]
            _ = popen_command(
                f"./build_and_push.sh {repo_name} ap-northeast-2 linux/amd64 ./",
                pwd=None
            )

        # 5. create service(ELB, ECS, Container Instance, domain)
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.LB)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.CONTAINER)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.COMPUTE)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, module=SUPPORTED_MODULE.DOMAIN)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        refresh_output()

        # 6. get domain
        stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        output: dict[str, str] = json.loads(stdout)
        if output.get("domain_name"):
            domain_name = output["domain_name"]["value"]
            print("#" * 100)
            typer.echo(typer.style(f"Domain Name: {domain_name}", fg=typer.colors.GREEN, bold=True))
            print("#" * 100)
    except typer.Abort:
        _ = popen_command(TERRAFORM_COMMAND.DESTROY)

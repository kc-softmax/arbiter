import typer
import os
import pathlib
import json
import asyncio
from typing import Optional
from alembic.config import Config as AlembicConfig

from arbiter.cli.utils import AsyncTyper
from arbiter.cli.utils import (
    read_config,
    write_config,
    refresh_output,
    popen_command,
    check_db_server,
    check_cache_server,
    TERRAFORM_COMMAND,
    SUPPORTED_MODULE,
)


app = AsyncTyper()


@app.command()
def dev():
    # 1. 실행시킬 서비스를 어떻게 알 것인가?(service, db, cache, app …)
    # 2. 알았으면 어떻게 실행시킬 것인가?(container, real service)
    # yaml에서 db 정보를 관리한다
    # db와 cache 서비스를 준비한다(동작하는지 확인만한다)
    config = read_config("arbiter.setting.ini")
    loop = asyncio.get_event_loop()
    db_status = loop.run_until_complete(check_db_server(
        drivername=config.get("database.dev", "engine"),
        username=config.get("database.dev", "username"),
        password=config.get("database.dev", "password"),
        hostname=config.get("database.dev", "hostname"),
        port=config.get("database.dev", "port"),
    ))
    if not db_status:
        typer.echo(typer.style("please, check your database service", fg=typer.colors.RED, bold=True))
        raise typer.Abort()
    typer.echo(typer.style("database access success", fg=typer.colors.GREEN, bold=True))

    cache_status = check_cache_server(
        url=config.get("cache", "redis.url")
    )
    if not cache_status:
        typer.echo(typer.style("please, check your redis service", fg=typer.colors.RED, bold=True))
        raise typer.Abort()
    typer.echo(typer.style("redis access success", fg=typer.colors.GREEN, bold=True))


@app.command()
def local():
    pass


@app.command()
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
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.NETWORK)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.SG)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()

        # 2. create cache
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.CACHE)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        refresh_output(pwd)

        # 3. get endpoint
        stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT, pwd)
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
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.IMAGES)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        refresh_output(pwd)
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
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.LB)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.CONTAINER)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.COMPUTE)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        stderr = popen_command(TERRAFORM_COMMAND.APPLY, SUPPORTED_MODULE.DOMAIN)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        refresh_output(pwd)

        # 6. get domain
        stdout, stderr = popen_command(TERRAFORM_COMMAND.OUTPUT)
        if stderr:
            typer.echo(typer.style(stderr, fg=typer.colors.RED, bold=True))
            raise typer.Abort()
        output: dict[str, str] = json.loads(stdout)
        if output.get("domain"):
            domain_name = output["domain"]["value"]
            print("#" * 100)
            typer.echo(typer.style(f"Domain: {domain_name}", fg=typer.colors.GREEN, bold=True))
            print("#" * 100)
    except typer.Abort:
        _ = popen_command(TERRAFORM_COMMAND.DESTROY)

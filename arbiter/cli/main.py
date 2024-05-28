import os
import typer
import subprocess
import json
import asyncio
import sys
from io import TextIOWrapper
from typing import Optional
from typing_extensions import Annotated
from mako.template import Template
from contextlib import asynccontextmanager

from arbiter.cli import PROJECT_NAME, CONFIG_FILE
from arbiter.cli.commands.database import app as database_app
from arbiter.cli.commands.build import app as build_app
from arbiter.cli.utils import read_config, SHORTCUT

app = typer.Typer()
app.add_typer(database_app, name="db", help="Execute commands for database creation and migration.")
app.add_typer(build_app, name="build", rich_help_panel="build environment",
    help="Configure build environment for deploying service"
)


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
def dev(
    app_path: Annotated[Optional[str], typer.Argument(..., help="The path to the FastAPI app, e.g., 'myapp.main:app'")] = f"{PROJECT_NAME}.main:arbiterApp",
    host: str = typer.Option(None, "--host", "-h", help="The host of the Arbiter FastAPI app."),
    port: int = typer.Option(8080, "--port", "-p", help="The port of the Arbiter FastAPI app."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for code changes.")
):
    """
    Read the config file.
    """
    # list of commands
    pids: dict[str, int] = {}
    commands: list[str] = []
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
    commands.append(uvicorn_command)

    installed_apps = config.get("installed_apps", "apps")
    apps = json.loads(installed_apps)
    for app in apps:
        if reload:
            commands.append(f"pymon {app}.py")
        else:
            commands.append(f"python {app}.py")

    async def run_command(command: str):
        proc = await asyncio.create_subprocess_shell(
            command,
            shell=True,
        )
        pids["app" if "uvicorn" in command else "service"] = proc.pid
        await proc.communicate()

    @asynccontextmanager
    async def raw_mode(file: TextIOWrapper):
        import termios
        old_attrs = termios.tcgetattr(file.fileno())
        new_attrs = old_attrs[:]
        new_attrs[3] = new_attrs[3] & ~(termios.ECHO | termios.ICANON)
        try:
            termios.tcsetattr(file.fileno(), termios.TCSADRAIN, new_attrs)
            yield
        finally:
            termios.tcsetattr(file.fileno(), termios.TCSADRAIN, old_attrs)

    async def interact(loop: asyncio.AbstractEventLoop, reload: bool):
        await asyncio.sleep(2)
        # key 입력을 계속 기다리지않고 바로 내보낸다
        typer.echo(typer.style("Arbiter CLI Options", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("Usage: ...", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("  Commands:", fg=typer.colors.CYAN, bold=True))
        typer.echo(typer.style("    p    display running process name and id", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("    k    kill running process with name", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("    s    start registered service or app", fg=typer.colors.WHITE, bold=True))
        async with raw_mode(sys.stdin):
            while True:
                await asyncio.sleep(0.001)
                option = sys.stdin.read(1)
                match option:
                    case SHORTCUT.SHOW_PROCESS:
                        for service, pid in pids.items():
                            typer.echo(typer.style(f"{service}: {pid}", fg=typer.colors.GREEN, bold=True))
                    case SHORTCUT.KILL_PROCESS:
                        import signal
                        typer.echo(typer.style(f"kill process number {[f'{key}({key[0]})' for key in pids.keys()]}", fg=typer.colors.WHITE, bold=True))
                        option = sys.stdin.read(1)
                        for key, pid in pids.items():
                            if option == key[0]:
                                os.kill(pids[key], signal.SIGTERM)
                                typer.echo(typer.style(f"killed {key}.....", fg=typer.colors.RED, bold=True))
                                pids.pop(key)
                                break
                    case SHORTCUT.START_PROCESS:
                        for app in apps:
                            if "service" not in pids.keys():
                                if reload:
                                    loop.create_task(run_command(f"pymon {app}.py"))
                                else:
                                    loop.create_task(run_command(f"python {app}.py"))
                        if "app" not in pids.keys():
                            loop.create_task(run_command(uvicorn_command))

                        typer.echo(typer.style(f"started service!!!!!!", fg=typer.colors.GREEN, bold=True))
                    case _:
                        continue

    async def waiting_until_finish(loop: asyncio.AbstractEventLoop, commands: list[str], reload: bool):
        tasks = []
        for command in commands:
            task = asyncio.create_task(run_command(command))
            tasks.append(task)
        tasks.append(asyncio.create_task(interact(loop, reload)))
        for task in tasks:
            await task

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(waiting_until_finish(loop, commands, reload))
    finally:
        import time
        time.sleep(1)


if __name__ == "__main__":
    app()

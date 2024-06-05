import os
import typer
import subprocess
import pathlib
import asyncio
import sys
import signal
from importlib import import_module
from io import TextIOWrapper
from typing import Optional
from typing_extensions import Annotated
from mako.template import Template
from contextlib import asynccontextmanager

from arbiter.cli import PROJECT_NAME, CONFIG_FILE
from arbiter.cli.commands.database import app as database_app
from arbiter.cli.commands.build import app as build_app
from arbiter.cli.utils import (
    read_config,
    Shortcut,
    popen_command,
    Commands,
    find_python_files_in_path,
    get_command,
)

app = typer.Typer()
app.add_typer(database_app, name="db",
              help="Execute commands for database creation and migration.")
app.add_typer(build_app, name="build", rich_help_panel="build environment",
              help="Configure build environment for deploying service"
              )


@app.command()
def init(
    base_path: Optional[str] = typer.Option(
        ".", "--path", "-p", help="The base path where to create the project.")
):
    """
    Creates a basic project structure with predefined files and directories.
    # """
    _create_project_structure(base_path)
    """
    initialize prisma db
    """
    package_path = os.path.dirname(os.path.abspath(__file__))
    root_path = pathlib.Path(package_path)
    pwd = f'{str(root_path.parent)}/database'
    popen_command(Commands.PRISMA_PUSH, pwd=pwd)
    popen_command(Commands.PRISMA_GENERATE, pwd=pwd)
    typer.echo(f"Project created successfully.")


@app.command()
def start(
    app_path: Annotated[Optional[str], typer.Argument(
        ..., help="The path to the FastAPI app, e.g., 'myapp.main:app'")] = f"{PROJECT_NAME}.main:arbiterApp",
    host: str = typer.Option(None, "--host", "-h",
                             help="The host of the Arbiter FastAPI app."),
    port: int = typer.Option(None, "--port", "-p",
                             help="The port of the Arbiter FastAPI app."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for code changes.")
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
        typer.echo(
            "Set the port and host in 'arbiter.settings.ini' or give them as options.")
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
                            of.write(template.render(
                                project_name=PROJECT_NAME))
                        else:
                            of.write(template.render())


@app.command()
def dev(
    app_path: Annotated[Optional[str], typer.Argument(
        ..., help="The path to the FastAPI app, e.g., 'myapp.main:app'")] = f"{PROJECT_NAME}.main:arbiterApp",
    host: str = typer.Option(None, "--host", "-h",
                             help="The host of the Arbiter FastAPI app."),
    port: int = typer.Option(8080, "--port", "-p",
                             help="The port of the Arbiter FastAPI app."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for code changes.")
):
    # This package used in only this function
    import uvicorn

    from watchfiles import awatch
    # You add your execute path for starting uvicorn app
    sys.path.insert(0, os.getcwd())
    """
    Read the config file.
    """
    # dict of commands with app name
    process_tasks: dict[str, asyncio.Task] = {}
    process_commands: dict[str, str] = {}
    service_order: dict[str, int] = {}
    pids: dict[str, int] = {}
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
        typer.echo(
            "Set the port and host in 'arbiter.settings.ini' or give them as options.")
        return

    """
    Starts the Arbiter FastAPI app using Uvicorn.
    """
    typer.echo("Starting FastAPI app...")
    
    apps = find_python_files_in_path()
    for app_name in apps:
        import_module(app_name)

    for service in AbstractServiceTemp.__subclasses__():
        process_commands[service.__module__] = get_command(service.__module__, service.__name__)

    def show_shortcut_info():
        typer.echo(typer.style("Arbiter CLI Options",
                   fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("Usage: ...", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("  Commands:", fg=typer.colors.CYAN, bold=True))
        typer.echo(typer.style("\th\tshow shortcut command",
                   fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\ta\tdisplay all service name and id", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\tr\tdisplay running service name and id", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\tk\tkill running process with name", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\ts\tstart registered service or app", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("\tq\texit",
                   fg=typer.colors.WHITE, bold=True))

    async def run_command(idx: int, command: str):
        # Run subprocess shell command
        proc = await asyncio.create_subprocess_shell(
            command,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )
        pids[idx] = proc.pid
        _, err = await proc.communicate()
        typer.echo(typer.style(err.decode(),
                   fg=typer.colors.YELLOW, bold=True))

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

    async def connect_stdin_stdout() -> asyncio.StreamReader:
        """stream stdin
        This function help stdin as async

        Returns:
            asyncio.StreamReader: stream
        """
        _loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await _loop.connect_read_pipe(lambda: protocol, sys.stdin)
        return reader

    async def interact(reload: bool):
        await asyncio.sleep(2)
        show_shortcut_info()
        signal.signal(signal.SIGINT, sigint_handler)
        signal.signal(signal.SIGTERM, sigint_handler)
        reader = await connect_stdin_stdout()
        async with raw_mode(sys.stdin):
            while True:
                encoded_option = await reader.read(100)
                option = encoded_option.decode()
                match option:
                    case Shortcut.SHOW_ALL_PROCESS:
                        typer.echo(typer.style(f"All of Service",
                                   fg=typer.colors.GREEN, bold=True))
                        for idx, service in enumerate(process_commands.keys(), start=1):
                            typer.echo(typer.style(
                                f"{idx}. {service}", fg=typer.colors.YELLOW, bold=True))
                    case Shortcut.SHOW_RUNNING_PROCESS:
                        typer.echo(typer.style(f"Running service",
                                   fg=typer.colors.GREEN, bold=True))
                        for idx, service in enumerate(process_tasks.keys(), start=1):
                            typer.echo(typer.style(
                                f"{idx}. {service}", fg=typer.colors.YELLOW, bold=True))
                    case Shortcut.KILL_PROCESS:
                        typer.echo(typer.style(f"kill order of service(press number of service):",
                                   fg=typer.colors.WHITE, bold=True))
                        encoded_option = await reader.read(100)
                        option = int(encoded_option.decode())
                        if option in pids:
                            for service in process_commands.keys():
                                try:
                                    os.kill(pids[option], signal.SIGTERM)
                                    process_tasks.pop(service)
                                    typer.echo(typer.style(
                                        f"shutdown {service}.....", fg=typer.colors.RED, bold=True))
                                except Exception as err:
                                    typer.echo(typer.style(
                                        f"already killed {service}.....", fg=typer.colors.YELLOW, bold=True))
                        else:
                            typer.echo(typer.style(
                                f"check service order", fg=typer.colors.YELLOW, bold=True))
                    case Shortcut.START_PROCESS:
                        typer.echo(typer.style(f"start order of service(press number of service):",
                            fg=typer.colors.WHITE, bold=True))
                        encoded_option = await reader.read(100)
                        option = int(encoded_option.decode())
                        if option in pids:
                            typer.echo(typer.style(f"already running...",
                                fg=typer.colors.YELLOW, bold=True))
                            for app_name, command in process_commands.items():
                                if not process_tasks.get(app_name):
                                    process_tasks[app_name] = asyncio.create_task(
                                        run_command(app_name, command))
                        else:
                            pass
                        # if not process_tasks.get("arbiter"):
                        #     process_tasks["arbiter"] = asyncio.create_task(
                        #         run_uvicorn(reload))

                        typer.echo(typer.style(
                            f"started all of service", fg=typer.colors.GREEN, bold=True))
                    case Shortcut.SHOW_SHORTCUT:
                        show_shortcut_info()
                    case Shortcut.EXIT:
                        typer.echo(typer.style(f"closing arbiter.....",
                                   fg=typer.colors.YELLOW, bold=True))
                        break
                    case _:
                        continue

    async def run_uvicorn(reload: bool):
        config = uvicorn.Config(
            app_path,
            host=host,
            port=port,
        )
        server = uvicorn.Server(config)
        socket = config.bind_socket()
        try:
            # If you add reload option, it will watch your present directory path
            async def watch_in_files(reload: bool):
                signal.signal(signal.SIGINT, sigint_handler)
                signal.signal(signal.SIGTERM, sigint_handler)
                if reload:
                    async for _ in awatch(os.getcwd()):
                        server.should_exit = True
                        await server.shutdown()
                        await server.startup()
            await asyncio.gather(server.serve([socket]), watch_in_files(reload), return_exceptions=True)
        except asyncio.CancelledError:
            await server.shutdown([socket])

    async def waiting_until_finish(process_commands: dict[str, str], reload: bool):
        # process_tasks["arbiter"] = asyncio.create_task(run_uvicorn(reload))
        for idx, (app_name, command) in enumerate(process_commands.items(), start=1):
            process_tasks[app_name] = asyncio.create_task(run_command(idx, command))
        return await interact(reload)

    def sigint_handler(sig, frame):
        """
        Return without error on SIGINT or SIGTERM signals in interactive command mode.

        e.g. CTRL+C or kill <PID>
        """
        sys.exit(1)

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(waiting_until_finish(
            process_commands, reload))
    finally:
        import time
        time.sleep(1)


if __name__ == "__main__":
    app()

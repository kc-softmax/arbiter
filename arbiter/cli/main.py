import os
import pathlib
import typer
import asyncio
import sys
import signal
from rich import print as rprint
from io import TextIOWrapper
from typing import Optional
from typing_extensions import Annotated
from mako.template import Template
from contextlib import asynccontextmanager
from arbiter.cli.utils import (
    get_running_command,
    read_config,
)
from arbiter.cli.commands.build import app as build_app
from arbiter.cli import PROJECT_NAME, CONFIG_FILE
from arbiter.constants.enums import (
    ArbiterCliCommand,
    ArbiterInitTaskResult,
    ArbiterShutdownTaskResult
)


app = typer.Typer()
app.add_typer(
    build_app,
    name="build",
    rich_help_panel="build environment",
    help="Configure build environment for deploying service")


@app.command()
def init(
    base_path: Optional[str] = typer.Option(
        ".", "--path", "-p", help="The base path where to create the project.")
):
    """
    Creates a basic project structure with predefined files and directories.
    # """
    _create_project_structure(base_path)
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

    sys.path.insert(0, os.getcwd())
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
    template_root_path = f'{os.path.abspath(
        os.path.dirname(__file__))}/templates'
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
    from arbiter import Arbiter, Service

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

    @asynccontextmanager
    async def interact(reader: asyncio.StreamReader):
        async def generate_input(reader: asyncio.StreamReader):
            while True:
                encoded_option = await reader.read(100)
                option = encoded_option.decode().upper().strip()
                match option:
                    case ArbiterCliCommand.Q.name:
                        break
                    case _:
                        yield option
                        continue

        async with raw_mode(sys.stdin):
            try:
                input_generator = generate_input(reader)
                yield input_generator
            except Exception as e:
                typer.echo(
                    typer.style(
                        f"An error occurred while running interact mode..\n{
                            e}",
                        fg=typer.colors.YELLOW, bold=True))
            finally:
                pass
                # typer.echo(
                #     typer.style(
                #         "Exiting interact mode...",
                #         fg=typer.colors.YELLOW, bold=True))

    async def service_stream_manager(aribter: Arbiter):
        async def read_stream(stream: asyncio.StreamReader, stream_name: str, is_stderr: bool = False):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded_line = line.decode().strip()
                if not decoded_line:
                    continue
                # decoded_line = decoded_line[:-4]
                if is_stderr:
                    rprint(
                        f"[bold yellow][{stream_name}][/bold yellow] [bold red]{decoded_line}[/bold red]")
                else:
                    rprint(
                        f"[bold yellow][{stream_name}][/bold yellow] {decoded_line}")
        while True:
            service = await aribter.pending_service_queue.get()
            if service is None:
                break
            command = get_running_command(
                service.service_meta.module_name,
                service.service_meta.name,
                service.id,
                aribter.node_id
            )
            process = await asyncio.create_subprocess_shell(
                f'{sys.executable} -c "{command}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'},
                shell=True
            )
            stream_name = f"{service.service_meta.name}: {service.id}"

            asyncio.create_task(
                read_stream(process.stdout, stream_name))
            asyncio.create_task(
                read_stream(process.stderr, stream_name, True))

    async def waiting_until_finish(reload: bool):
        def show_shortcut_info():
            typer.echo(typer.style("Commands:",
                       fg=typer.colors.CYAN, bold=True))
            for shortcut in ArbiterCliCommand:
                typer.echo(typer.style(
                    shortcut.get_typer_text(),
                    fg=typer.colors.WHITE, bold=True))

        reader = await connect_stdin_stdout()

        async with Arbiter().start() as arbiter:
            # occur error when arbiter is started
            if not isinstance(arbiter, Arbiter):
                typer.echo(
                    typer.style(
                        f"{arbiter}.....",
                        fg=typer.colors.BRIGHT_RED, bold=True))
                return
            # 이 부분에서 service와 같이 기다린다.
            # 서비스가 중간에 추가되고 하니까 그것도 생각해야 한다.
            async with interact(reader) as commands:
                stream_task = asyncio.create_task(
                    service_stream_manager(arbiter))
                async for result, message in arbiter.initial_task():
                    # print progress message
                    match result:
                        case ArbiterInitTaskResult.SUCCESS:
                            typer.echo(
                                typer.style(
                                    f"All services are started successfully.",
                                    fg=typer.colors.BRIGHT_GREEN, bold=True))
                        case ArbiterInitTaskResult.FAIL:
                            typer.echo(
                                typer.style(
                                    f"failed to start services {message}",
                                    fg=typer.colors.RED, bold=True))
                    show_shortcut_info()
                    # 여기서 process queue를 구독하는 taskf를 만든다..?
                    async for command in commands:
                        if command.upper() not in ArbiterCliCommand.__members__:
                            typer.echo(
                                typer.style(
                                    f"Invalid command {command}",
                                    fg=typer.colors.RED, bold=True))
                    # await stream_task
            typer.echo(
                typer.style(
                    f"Arbiter is shutting down",
                    fg=typer.colors.YELLOW, bold=True))
            async for result, message in arbiter.shutdown_task():
                match result:
                    case ArbiterShutdownTaskResult.SUCCESS:
                        typer.echo(
                            typer.style(
                                f"All services are stopped successfully.",
                                fg=typer.colors.BRIGHT_GREEN, bold=True))
                    case ArbiterShutdownTaskResult.WARNING:
                        typer.echo(
                            typer.style(
                                f"In shutdown catch warning {message}",
                                fg=typer.colors.YELLOW, bold=True))

        typer.echo(
            typer.style(
                "shutdown is completed",
                fg=typer.colors.YELLOW, bold=True))

    """
        1. initialize arbiter
        2. start arbiter
            2.1 register and start services
            2.2 start api service
            2.3 check all rpc function is fine
            2.4 wait for the all service is activated
        3. start interact task
        
        arbiter shutdown event is triggered by interact task or arbiter task
    """

    typer.echo(
        typer.style(
            'Arbiter is starting...',
            fg=typer.colors.BRIGHT_GREEN, bold=True))

    sys.path.insert(0, os.getcwd())
    """
    Read the config file.
    """

    # config = read_config(CONFIG_FILE)
    # if (config is None):
    #     typer.echo("No config file path found. Please run 'init' first.")
    #     return

    # """
    # Get the "host" and "port" from config file.
    # """
    # host = host or config.get("fastapi", "host", fallback=None)
    # port = port or config.get("fastapi", "port", fallback=None)
    # if (host is None or port is None):
    #     typer.echo(
    #         "Set the port and host in 'arbiter.settings.ini' or give them as options.")
    #     return
    try:
        asyncio.run(waiting_until_finish(reload))
    except SystemExit as e:
        print(f"SystemExit caught in main: {e.code}")
    except Exception as e:
        print(f"Unhandled exception in main: {e}")
    finally:
        # asyncio.run(shutdown_event.wait())
        import time


if __name__ == "__main__":
    app()

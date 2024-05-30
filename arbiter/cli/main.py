import os
import typer
import subprocess
import json
import asyncio
import sys
import signal
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
    import uvicorn

    from watchfiles import awatch
    # You add your execute path for starting uvicorn app
    sys.path.insert(0, os.getcwd())
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

    installed_apps = config.get("installed_apps", "apps")
    apps = json.loads(installed_apps)
    for app in apps:
        commands.append(f"python {app}.py")

    def show_shortcut_info():
        typer.echo(typer.style("Arbiter CLI Options", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("Usage: ...", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("  Commands:", fg=typer.colors.CYAN, bold=True))
        typer.echo(typer.style("    h    show shortcut command", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("    p    display running process name and id", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("    k    kill running process with name", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("    s    start registered service or app", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("    q    exit", fg=typer.colors.WHITE, bold=True))

    async def run_command(command: str):
        proc = await asyncio.create_subprocess_shell(
            command,
            shell=True,
        )
        pids["service"] = proc.pid
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

    async def connect_stdin_stdout() -> list[asyncio.StreamReader | asyncio.StreamWriter]:
        """stream stdin
        This function help stdin as async
        
        Returns:
            list[asyncio.StreamReader | asyncio.StreamWriter]: stream
        """
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
        writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
        return reader, writer

    async def interact(loop: asyncio.AbstractEventLoop, reload: bool):
        await asyncio.sleep(2)
        show_shortcut_info()
        signal.signal(signal.SIGINT, sigint_handler)
        signal.signal(signal.SIGTERM, sigint_handler)
        reader, _ = await connect_stdin_stdout()
        async with raw_mode(sys.stdin):
            while True:
                encoded_option = await reader.read(100)
                option = encoded_option.decode()
                match option:
                    case SHORTCUT.SHOW_PROCESS:
                        typer.echo(typer.style(f"Running List", fg=typer.colors.GREEN, bold=True))
                        for service in pids.keys():
                            typer.echo(typer.style(f"{service}", fg=typer.colors.YELLOW, bold=True))
                    case SHORTCUT.KILL_PROCESS:
                        typer.echo(typer.style(f"kill all of process", fg=typer.colors.WHITE, bold=True))
                        pids["app"].cancel()
                        for key, pid in pids.items():
                            if isinstance(pid, int):
                                os.kill(pid, signal.SIGTERM)
                                typer.echo(typer.style(f"shutdown {key}.....", fg=typer.colors.RED, bold=True))
                        pids.clear()
                    case SHORTCUT.START_PROCESS:
                        for app in apps:
                            if not pids.get("service"):
                                loop.create_task(run_command(f"python {app}.py"))
                        if not pids.get("app"):
                            uvicorn_task = loop.create_task(run_uvicorn())
                            pids["app"] = uvicorn_task

                        typer.echo(typer.style(f"started all of service", fg=typer.colors.GREEN, bold=True))
                    case SHORTCUT.SHOW_SHORTCUT:
                        show_shortcut_info()
                    case SHORTCUT.EXIT:
                        for key, pid in pids.items():
                            if isinstance(pid, int):
                                os.kill(pid, signal.SIGTERM)
                        sys.exit(0)
                    case _:
                        continue

    async def run_uvicorn():
        config = uvicorn.Config(
            app_path,
            host=host,
            port=port,
        )
        server = uvicorn.Server(config)
        socket = config.bind_socket()
        try:
            # If you add reload option, it will watch your present directory path
            if reload:
                async def watch_in_files():
                    signal.signal(signal.SIGINT, sigint_handler)
                    signal.signal(signal.SIGTERM, sigint_handler)
                    async for _ in awatch(os.getcwd()):
                        server.should_exit = True
                        await server.shutdown()
                        await server.startup()
                await asyncio.gather(server.serve([socket]), watch_in_files(), return_exceptions=True)
            else:
                await server.serve([socket])
        except asyncio.CancelledError:
            typer.echo(typer.style(f"shutdown app.......", fg=typer.colors.RED, bold=True))
            await server.shutdown([socket])

    async def waiting_until_finish(loop: asyncio.AbstractEventLoop, commands: list[str], reload: bool):
        tasks = []
        app_task = asyncio.create_task(run_uvicorn())
        pids["app"] = app_task
        tasks.append(app_task)
        for command in commands:
            service_task = asyncio.create_task(run_command(command))
            tasks.append(service_task)
        return await interact(loop, reload)

    def sigint_handler(sig, frame):
        """
        Return without error on SIGINT or SIGTERM signals in interactive command mode.

        e.g. CTRL+C or kill <PID>
        """
        sys.exit(0)

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(waiting_until_finish(loop, commands, reload))
    finally:
        import time
        time.sleep(1)


if __name__ == "__main__":
    app()

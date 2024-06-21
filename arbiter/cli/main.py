import os
import pathlib
import typer
import asyncio
import sys
import signal
from io import TextIOWrapper
from typing import Optional
from typing_extensions import Annotated
from mako.template import Template
from contextlib import asynccontextmanager
from arbiter.cli.utils import (
    Commands,
    popen_command,
    read_config,
    Shortcut,
)
from arbiter.cli.commands.build import app as build_app
from arbiter.cli.commands.database import app as database_app
from arbiter.cli import PROJECT_NAME, CONFIG_FILE


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

    """
    Prisma
    """

    # asyncio.run(arbiter.start(app_path, host, port, reload))
    # async def run_command(command: str):
    #     print(f"Running command '{command}'...")
    #     # Run subprocess shell command
    #     proc = await asyncio.create_subprocess_shell(
    #         command,
    #         shell=True,
    #     )
    #     await proc.communicate()
    #     print(f"Command '{command}' finished")

    # async def run():
    #     # Run subprocess shell command
    #     uvicorn_command = f"uvicorn {app_path} --host {host} --port {port}"
    #     mewbiter = Mewbiter()
    #     print(f"Starting Arbiter...")
    #     mewbiter_task = asyncio.create_task(mewbiter.start())
    #     # ApiService
    #     asyncio.create_task(
    #         run_command(
    #             'python -c "from arbiter.api.api_service import ApiService; ApiService.launch()"')
    #     )

    #     # asyncio.create_task(
    #     #     run_command('python test_service.py')
    #     # )
    #     # asyncio.create_task(
    #     #     run_command('python test_service2.py')
    #     # )

    #     # asyncio.create_task(run_command(uvicorn_command))
    #     # Command to run Uvicorn with the FastAPI app
    #     await mewbiter_task

    # # Use subprocess to execute the command
    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(run())


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
    # 특정 조건에서만 실행가능하게 해야할까?
    # 임시로 선언 나중에 바꿔보자
    from arbiter import Arbiter
    # You add your execute path for starting uvicorn app
    arbiter = Arbiter()
    arbiter_task: asyncio.Task = None
    interact_task: asyncio.Task = None
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

    """
    Starts the Arbiter FastAPI app using Uvicorn.
    """

    def show_shortcut_info():
        typer.echo(typer.style("Arbiter CLI Options",
                   fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("Usage: ...", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("  Commands:", fg=typer.colors.CYAN, bold=True))
        typer.echo(typer.style("\th\tshow shortcut command",
                   fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\ta\tdisplay service list", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\tr\tdisplay active services", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\tk\tstop service", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style(
            "\ts\tstart service", fg=typer.colors.WHITE, bold=True))
        typer.echo(typer.style("\tq\texit",
                   fg=typer.colors.WHITE, bold=True))

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
        await asyncio.sleep(1)

        show_shortcut_info()
        reader = await connect_stdin_stdout()
        async with raw_mode(sys.stdin):
            while True:
                encoded_option = await reader.read(100)
                option = encoded_option.decode()
                match option:
                    case Shortcut.SHOW_SERVICE_LIST:
                        typer.echo(typer.style(f"services list",
                                   fg=typer.colors.GREEN, bold=True))
                        # TODO get function
                        services = await arbiter.services
                        for service in services:
                            if not arbiter.validate_service(service.name):
                                typer.echo(
                                    typer.style(
                                        f"{service.id}. {service.name} (unregistered)",
                                        fg=typer.colors.RED,
                                        overline=True
                                    ))
                            else:
                                typer.echo(
                                    typer.style(
                                        f"{service.id}. {service.name}",
                                        fg=typer.colors.YELLOW,
                                        bold=True))
                    case Shortcut.SHOW_ACTIVE_SERVICES:
                        typer.echo(typer.style(f"active services",
                                   fg=typer.colors.GREEN, bold=True))
                        # TODO get function
                        active_services = await arbiter.active_services
                        for idx, active_service in enumerate(active_services, start=1):
                            typer.echo(
                                typer.style(
                                    f"{idx}: {active_service.service_meta.name} ({active_service.id})",
                                    fg=typer.colors.YELLOW,
                                    bold=True))
                    case Shortcut.KILL_SERVICE:
                        typer.echo(typer.style(f"kill order of service(press number of service):",
                                   fg=typer.colors.WHITE, bold=True))
                        # TODO get function
                        active_services = await arbiter.active_services
                        for idx, active_service in enumerate(active_services, start=1):
                            typer.echo(
                                typer.style(
                                    f"{idx}: {active_service.service_meta.name} ({active_service.id})",
                                    fg=typer.colors.YELLOW,
                                    bold=True))
                        encoded_option = await reader.read(100)
                        option = int(encoded_option.decode())
                        service_id = active_services[option - 1].id
                        await arbiter.stop_services([service_id])
                    case Shortcut.START_SERVICE:
                        typer.echo(typer.style(f"start order of service(press number of service):",
                                               fg=typer.colors.WHITE, bold=True))
                        services = await arbiter.services
                        for idx, service in enumerate(services, start=1):
                            if not arbiter.validate_service(service.name):
                                typer.echo(
                                    typer.style(
                                        f"{idx}. {service.name} (unregistered)",
                                        fg=typer.colors.RED,
                                        overline=True
                                    ))
                            else:
                                typer.echo(
                                    typer.style(
                                        f"{idx}. {service.name}",
                                        fg=typer.colors.YELLOW,
                                        bold=True))

                        encoded_option = await reader.read(100)
                        option = int(encoded_option.decode())
                        service = services[option - 1]
                        if not arbiter.validate_service(service.name):
                            typer.echo(
                                typer.style(
                                    f"{service.name} is unregistered",
                                    fg=typer.colors.RED,
                                    bold=True))
                            continue
                        try:
                            asyncio.create_task(
                                arbiter.start_service(service.name))
                            typer.echo(
                                typer.style(
                                    f"{service.name} is starting",
                                    fg=typer.colors.GREEN,
                                    bold=True))
                        except Exception as e:
                            typer.echo(
                                typer.style(
                                    f"Error: {e}",
                                    fg=typer.colors.RED,
                                    bold=True))

                        # service_name = arbiter.services_number[option]
                        # arbiter.stop_service(service_name)
                        # typer.echo(typer.style(
                        #     f"shutdown {arbiter.services_number[option]}.....", fg=typer.colors.RED, bold=True))

                        # case Shortcut.SHOW_ALL_PROCESS:
                        #     typer.echo(typer.style(f"All of Service",
                        #                fg=typer.colors.GREEN, bold=True))
                        #     for idx, service in enumerate(arbiter.registered_services, start=1):
                        #         typer.echo(typer.style(
                        #             f"{idx}. {service.__name__}", fg=typer.colors.YELLOW, bold=True))
                        # case Shortcut.SHOW_RUNNING_PROCESS:
                        #     typer.echo(typer.style(f"Running service",
                        #                fg=typer.colors.GREEN, bold=True))
                        #     # TODO get function
                        #     for idx, service_name in enumerate(await arbiter.active_services, start=1):
                        #         typer.echo(typer.style(
                        #             f"{idx}. {service_name}", fg=typer.colors.YELLOW, bold=True))

                        # case Shortcut.KILL_PROCESS:
                        #     typer.echo(typer.style(f"kill order of service(press number of service):",
                        #                fg=typer.colors.WHITE, bold=True))
                        #     encoded_option = await reader.read(100)
                        #     option = int(encoded_option.decode())
                        #     # service_name = arbiter.services_number[option]
                        #     # arbiter.stop_service(service_name)
                        #     # typer.echo(typer.style(
                        #     #     f"shutdown {arbiter.services_number[option]}.....", fg=typer.colors.RED, bold=True))
                        # case Shortcut.START_PROCESS:
                        #     typer.echo(typer.style(f"start order of service(press number of service):",
                        #                            fg=typer.colors.WHITE, bold=True))
                        #     encoded_option = await reader.read(100)
                        #     option = int(encoded_option.decode())
                    case Shortcut.SHOW_SHORTCUT:
                        show_shortcut_info()
                    case Shortcut.EXIT:
                        break
                    case _:
                        continue

    async def waiting_until_finish(reload: bool):
        nonlocal arbiter_task
        nonlocal interact_task
        arbiter_task = asyncio.create_task(arbiter.start())
        interact_task = asyncio.create_task(interact(reload))

        for signame in {'SIGINT', 'SIGTERM'}:
            asyncio.get_running_loop().add_signal_handler(
                getattr(signal, signame),
                lambda: asyncio.ensure_future(signal_handler(signame)))

        # arbiter_task가 먼저 끝날 경우가 있을까:? (time out 발생)
        done, pending = await asyncio.wait(
            [arbiter_task, interact_task], return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            if task == interact_task:
                await arbiter.shutdown()
                await arbiter_task
            else:
                interact_task.cancel()
        typer.echo(
            typer.style(
                f"closing arbiter.....",
                fg=typer.colors.YELLOW, bold=True))

    async def signal_handler(signame: str):
        """
        Return without error on SIGINT or SIGTERM signals in interactive command mode.

        e.g. CTRL+C or kill <PID>
        """
        # nonlocal force_shutdown
        # nonlocal shutdown_event
        # force_shutdown = True
        # print(f"Received signal {signame}")
        # if interact_task:
        #     interact_task.cancel()
        # if arbiter_task:
        #     arbiter_task.cancel()

        # await asyncio.gather(interact_task, arbiter_task, return_exceptions=True)
        # await arbiter.shutdown()
        # print("Shutdown completed")
        # shutdown_event.set()

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

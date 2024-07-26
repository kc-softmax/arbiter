from asyncio.subprocess import Process
import os
import platform
import psutil
import signal
import typer
import asyncio
import sys
from rich.console import Console
from io import TextIOWrapper
from typing_extensions import Annotated
from mako.template import Template
from contextlib import asynccontextmanager, suppress
from arbiter.cli.utils import (
    get_running_command,
    read_config,
)
from arbiter.cli.commands.build import app as build_app
from arbiter.cli import PROJECT_NAME, CONFIG_FILE
from arbiter.constants.enums import (
    ArbiterCliCommand,
    WarpInPhase,
    WarpInTaskResult,
    ArbiterShutdownTaskResult
)


app = typer.Typer()
console = Console()
app.add_typer(
    build_app,
    name="build",
    rich_help_panel="build environment",
    help="Configure build environment for deploying service")


def get_os():
    system = platform.system()
    if system == "Darwin":
        return "OS X"
    elif system == "Linux":
        return "Linux"
    else:
        return "Other"


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

def show_shortcut_info(is_replica: bool = False):
    console.print("[bold cyan]Commands[/bold cyan]")
    for shortcut in ArbiterCliCommand:
        if is_replica and not shortcut == ArbiterCliCommand.Q:
            continue
        console.print(shortcut.get_typer_text())               


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

async def check_redis_running(name: str) -> bool:
    from redis.asyncio import ConnectionPool, Redis, ConnectionError
    try:
        from arbiter.cli import CONFIG_FILE
        from arbiter.cli.utils import read_config
        config = read_config(CONFIG_FILE)
        host = config.get("cache", "redis.url", fallback="localhost")
        port = config.get("cache", "cache", fallback="6379")
        redis_url = f"redis://{host}:{port}/{name}"
        async_redis_connection_pool = ConnectionPool.from_url(
            redis_url,
            socket_timeout=5,
        )
        redis = Redis(connection_pool=async_redis_connection_pool)
        await redis.ping()
        await redis.aclose()
        await async_redis_connection_pool.disconnect()
        return True
    except ConnectionError:
        return False

@asynccontextmanager
async def interact(command_queue: asyncio.Queue[Annotated[str, "command"]]):
    async def read_input(reader: asyncio.StreamReader):
        while True:
            input = await reader.read(100)
            input = input.decode().upper().strip()
            await command_queue.put(input)
    reader = await connect_stdin_stdout()
    task = asyncio.create_task(read_input(reader))
    try:
        yield command_queue
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


async def terminate_process(process: Process):
    try:
        kill_signal = signal.SIGTERM
        match get_os():
            case "Linux":
                kill_signal = signal.SIGKILL
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.send_signal(kill_signal)
        parent.send_signal(kill_signal)
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except asyncio.TimeoutError:
            for child in children:
                child.kill()
            parent.kill()
    except psutil.NoSuchProcess:
        pass
    except Exception as e:
        print(e)

async def start_process(command: str, process_name:str, shell: bool = True):
    async def read_stream(
        stream: asyncio.StreamReader,
        stream_name: str,
        header_color='yellow',
        content_color='white',
    ):
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded_line = line.decode().strip()
            if not decoded_line:
                continue
            console.print(f"[bold {header_color}][{stream_name}][/bold {header_color}] [{content_color}]{decoded_line}[/{content_color}]")

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, 'PYTHONUNBUFFERED': '1'},
        shell=shell
    )
    asyncio.create_task(
            read_stream(process.stdout, process_name))
    asyncio.create_task(
            read_stream(process.stderr, process_name, 'red'))
    return process


@app.command()
def dev(
    name: str = typer.Option(
        "Danimoth", "--name", help="Name of the arbiter to run."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for code changes."),
    log_level: str = typer.Option(
        "info", "--log-level", help="Log level for arbiter.")
):
    from arbiter.runner import ArbiterRunner, TypedQueue, Service
    command_queue: asyncio.Queue[Annotated[str, "command"]] = asyncio.Queue()
    async def arbiter_manager(
        arbiter_runner: ArbiterRunner,
        service_queue: TypedQueue[Service],
        command_queue: asyncio.Queue[Annotated[str, "command"]]
    ):
        while True:
            service = await service_queue.get()
            try:
                if service is None:
                    await command_queue.put(None)
                    break
            except Exception as e:
                print(e, ': manager')
                
            command = get_running_command(
                service.service_meta.module_name,
                service.service_meta.name,
                service.id,
                arbiter_runner.node.unique_id,
                arbiter_runner.name
            )
            
            process = await start_process(
                f'{sys.executable} -c "{command}"',
                f"{service.service_meta.name}: {service.id}")
            # start service success message
            console.print(
                f"[bold green]{arbiter_runner.name}[/bold green]'s [bold yellow]{service.service_meta.name}[/bold yellow] has warped in.")
       
    async def arbiter_run(
        name: str,
        config: dict[str, str],
        command_queue: asyncio.Queue[Annotated[str, "command"]],
        log_level: str,
        reload: bool
    ):          
        """
        Get the configure parameters from config file.
        """
        host = config.get("api", "host", fallback=None)
        port = config.get("api", "port", fallback=None)
        worker_count = config.get("api", "worker_count", fallback=1)
        
        console.print(f"[bold green]Warp In [bold yellow]Arbiter[/bold yellow] [bold green]{name}...[/bold green]")

        if not await check_redis_running(name):
            console.print("[bold red]Failed to start, connect redis issue.[/bold red]")
            console.print("[bold yellow]Check redis connection configuration in 'arbiter.settings.ini'[/bold yellow]")            
            console.print("[bold yellow]or Check if the Redis server is running.  [/bold yellow]")
            return
        
        if (host is None or port is None):
            console.print(
                "[bold red]Set the port and host in 'arbiter.settings.ini' or give them as options.[/bold red]")
            return
        try:
            manager_task = None
            failed_to_warp_in = False
            gunicorn_process = None
            async with ArbiterRunner(name=name).start(config) as arbiter_runner:
                async for result, message in arbiter_runner.warp_in(WarpInPhase.INITIATION):
                    match result:
                        # Danimoth is the warp-in master.
                        case WarpInTaskResult.IS_MASTER:
                            console.print(f"[bold green]{arbiter_runner.name}[/bold green] is the [bold green]Master[/bold green].")
                        case WarpInTaskResult.IS_REPLICA:
                            console.print(f"[bold green]{arbiter_runner.name}[/bold green] is the [bold blue]Replica[/bold blue].")
                        case WarpInTaskResult.FAIL:
                            console.print(f"[bold red]Failed to warp in[/bold red] {message}")
                            failed_to_warp_in = True
                if failed_to_warp_in:
                    return
                if not arbiter_runner.is_replica:
                    # env에 넣어야 한다.
                    # start gunicorn process, and check it is running
                    gunicorn_command = ' '.join([
                        f'ARBITER_NAME={name},',
                        f'NODE_ID={arbiter_runner.node.unique_id}',
                        'gunicorn',
                        '-w', f"{worker_count}",  # Number of workers
                        '--bind', f"{host}:{port}",  # Bind to port 8080
                        '-k', 'arbiter.api.ArbiterUvicornWorker',  # Uvicorn worker class
                        '--log-level', log_level,  # Log level
                        'arbiter.api:get_app'  # Application module and variable
                    ])
                    gunicorn_process = await start_process(gunicorn_command, 'gunicorn')
                    registered_gunicorn_worker_count = 0
                    # must be set timeout
                    async for result, message in arbiter_runner.warp_in(WarpInPhase.CHANNELING):
                        match result:
                            case WarpInTaskResult.API_REGISTER_SUCCESS:
                                registered_gunicorn_worker_count += 1
                            case WarpInTaskResult.FAIL:
                                console.print(f"[bold red]Failed to warp in[/bold red] {message}")
                                if gunicorn_process:
                                    console.print(f"[bold red]{arbiter_runner.name}[/bold red] terminating gunicorn process...")
                                    await terminate_process(gunicorn_process)
                                    return        
                            # has warped in.
                        if int(worker_count) == registered_gunicorn_worker_count:
                            console.print(f"[bold green]{arbiter_runner.name}[/bold green]'s [bold yellow]WebServer[/bold yellow] has warped in with [bold green]{worker_count}[/bold green] workers.")
                            break                            
                            
                manager_task = asyncio.create_task(
                    arbiter_manager(
                        arbiter_runner, 
                        arbiter_runner.pending_service_queue,
                        command_queue
                    ))
                
                # process manager? task 를 실행한다.
                async for result, message in arbiter_runner.warp_in(WarpInPhase.MATERIALIZATION):
                    # print progress message
                    match result:
                        case WarpInTaskResult.SUCCESS:
                            console.print(
                                f"[bold green]{arbiter_runner.name}[/bold green]'s warp-in [bold green]Completed[bold green].")
                            break
                        case WarpInTaskResult.FAIL:
                            console.print(f"[bold red]Failed to warp in[/bold red] {message}")
                            break
                
                # 함수등록의 경우 어떻게 해야할까? 내일 고민해보자
                
                ## MARK 레플리카의 경우 마스터의 명령이나 로그를 출력해준다.
                ## 공통적으로 시스템 로그를 출력해주는 queue가 필요할까?
                async with raw_mode(sys.stdin):
                    async with interact(command_queue=command_queue):
                        # replica의 경우 마스터의 명령을 받아야한다.
                        # 종료메세지만 알려주도록 하자,
                        show_shortcut_info(arbiter_runner.is_replica)
                        while True:
                            command = await command_queue.get()
                            if command is None:
                                break
                            match command:
                                case ArbiterCliCommand.Q.name:
                                    break
                                case _:
                                    console.print(
                                        f"[bold red]Invalid command {command}[/bold red]")
                
                console.print(f"[bold red]{arbiter_runner.name}[/bold red] is warp out...")

                if gunicorn_process:
                    try:
                        console.print(f"[bold red]{arbiter_runner.name}[/bold red] terminating gunicorn process...")
                        await terminate_process(gunicorn_process)               
                    except Exception as e:
                        console.print(f"[bold red]{arbiter_runner.name}[/bold red] {e}")
                try:
                    async for result, message in arbiter_runner.shutdown_task():
                        match result:
                            case ArbiterShutdownTaskResult.SUCCESS:
                                # Danimoth's warp-out completed.
                                console.print(f"[bold green]{arbiter_runner.name}[/bold green]'s warp-out [bold green]Completed[bold green].")
                            case ArbiterShutdownTaskResult.WARNING:
                                console.log(f"[bold yellow]{arbiter_runner.name}[/bold yellow]'s warp-out catch warning {message}")
                except Exception as e:
                    console.print(f"[bold red]{arbiter_runner.name}[/bold red] e{e}")
        except Exception as e:
            console.print("[bold red]An error occurred while running the arbiter[/bold red]")
        manager_task and manager_task.cancel()
        
    async def async_shutdown_signal_handler():
        await command_queue.put(None)

    def shutdown_signal_handler():
        asyncio.ensure_future(async_shutdown_signal_handler())
    
    # async def terminate_all_processes():
    #     for process in processes:
    #         try:
    #             await terminate_process(process)               
    #         except ProcessLookupError as e:
    #             pass
    #         except Exception as e:
    #             console.print(f"Error during termination: {e}")
        
    sys.path.insert(0, os.getcwd())
    """
    Read the config file.
    """

    config = read_config(CONFIG_FILE)
    if config is None:
        create_config()
        config = read_config(CONFIG_FILE)

    try:
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, lambda s, f: shutdown_signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: shutdown_signal_handler())
    
        asyncio.run(
            arbiter_run(
                name,
                config,
                command_queue,
                log_level,
                reload))
    except SystemExit as e:
        console.print(f"SystemExit caught in main: {e.code}")
    except KeyboardInterrupt:
        console.print("KeyboardInterrupt caught in main")
    except Exception as e:
        console.print(f"Unhandled exception in main: {e}")
    # finally:
    #     asyncio.run(terminate_all_processes())

if __name__ == "__main__":
    app()

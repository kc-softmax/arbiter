import signal
import typer
import asyncio
from configparser import ConfigParser
from rich.console import Console
from typing_extensions import Annotated
from arbiter.enums import (
    ArbiterCliCommand,
    WarpInPhase,
    WarpInTaskResult,
)
from arbiter.utils import (
    check_redis_running,
    read_config,
    get_arbiter_setting,
)
from arbiter.runner.utils import (
    create_config,
)
from arbiter.constants import CONFIG_FILE
from arbiter.runner.interface import TerminalInterface
from arbiter.app import ArbiterApp

console = Console()

class ArbiterRunner:
        
    @staticmethod
    def run(
        app: ArbiterApp,
        name: str = typer.Option(
            "Danimoth", "--name", help="Name of the arbiter to run."),
        reload: bool = typer.Option(
            False, "--reload", help="Enable auto-reload for code changes."),
        log_level: str = typer.Option(
            "info", "--log-level", help="Log level for arbiter.")
    ):
        def shutdown_signal_handler(_system_queue: asyncio.Queue[Annotated[str, "command"]]):
            asyncio.ensure_future(async_shutdown_signal_handler(_system_queue))

        async def async_shutdown_signal_handler(_system_queue: asyncio.Queue[Annotated[str, "command"]]):
            await _system_queue.put(None)
            
        async def arbiter_run(
            arbiter_app: ArbiterApp,
            config: ConfigParser,
            system_queue: asyncio.Queue[Annotated[str, "command"]],
        ):          
            """
            Get the configure parameters from config file.
            """
            
            if not await check_redis_running(
                host=config.get("broker", "host"),
                port=config.getint("broker", "port"),
                password=config.get("broker", "password"),
            ):
                console.print("[bold red]Failed to start, connect redis issue.[/bold red]")
                console.print("[bold yellow]Check redis connection configuration in 'arbiter.settings.ini'[/bold yellow]")            
                console.print("[bold yellow]or Check if the Redis server is running.  [/bold yellow]")
                return
            try:
                async with arbiter_app.warp_in(
                    system_queue=system_queue,
                ) as arbiter_runner:
                    try:
                        console.print(f"[bold green]Warp In [bold yellow]Arbiter[/bold yellow] [bold green]{arbiter_runner.name}...[/bold green]")
                        if arbiter_runner.arbiter_node.is_master:
                            console.print(f"[bold green]{arbiter_runner.name}[/bold green] is the [bold green]Master[/bold green].")
                        else:
                            console.print(f"[bold green]{arbiter_runner.name}[/bold green] is the [bold blue]Replica[/bold blue].")
                        
                        async for result, message in arbiter_runner.start_phase(WarpInPhase.PREPARATION):
                            match result:
                                # Danimoth is the warp-in master.
                                case WarpInTaskResult.SUCCESS:
                                    console.print(f"[bold green]{arbiter_runner.name}[/bold green] [bold yellow]{message}[/bold yellow].")
                                    break
                                case WarpInTaskResult.FAIL:
                                    raise Exception(message)

                        async for result, message in arbiter_runner.start_phase(WarpInPhase.INITIATION):
                            match result:
                                case WarpInTaskResult.SUCCESS:
                                    console.print(f"[bold green]{arbiter_runner.name}[/bold green] [bold yellow]{message}[/bold yellow].")
                                    break
                                case WarpInTaskResult.WARNING:
                                    console.print(f"[bold yellow]{arbiter_runner.name}[/bold yellow] [bold blue]{message}[/bold blue].")
                                case WarpInTaskResult.FAIL:
                                    raise Exception(message)

                        async for result, message in arbiter_runner.start_phase(WarpInPhase.MATERIALIZATION):
                            match result:
                                case WarpInTaskResult.SUCCESS:
                                    console.print(f"[bold green]{arbiter_runner.name}[/bold green] [bold yellow]{message}[/bold yellow].")
                                    break
                                case WarpInTaskResult.WARNING:
                                    console.print(f"[bold yellow]{arbiter_runner.name}[/bold yellow] [bold blue]{message}[/bold blue].")
                                case WarpInTaskResult.FAIL:
                                    raise Exception(message)
                                
                        # 함수등록의 경우 어떻게 해야할까? 내일 고민해보자
                        
                        ## MARK 레플리카의 경우 마스터의 명령이나 로그를 출력해준다.
                        ## 공통적으로 시스템 로그를 출력해주는 queue가 필요할까?
                        async with TerminalInterface(
                            system_queue=system_queue,
                        ) as system_queue:
                            system_queue.put_nowait(ArbiterCliCommand.H.name)
                            # need intro message
                            while True:
                                command = await system_queue.get()
                                if command is None:
                                    break
                                match command:
                                    case ArbiterCliCommand.Q.name:
                                        break
                                    case ArbiterCliCommand.R.name:
                                        await arbiter_runner._stop_service(1)
                                        pass
                                    case ArbiterCliCommand.H.name:
                                        console.print("[bold cyan]Commands[/bold cyan]")
                                        for shortcut in ArbiterCliCommand:
                                            console.print(shortcut.get_typer_text())
                                    case _:
                                        console.print(
                                            f"[bold red]Invalid command {command}[/bold red]")

                    except Exception as e:
                        # arbiter 를 소환 혹은 실행하는 도중 예외가 발생하면 처리한다.
                        console.print(f"[bold red]An error occurred when warp-in..[/bold red] {e}")
                    finally:
                        console.print(f"[bold red]{arbiter_runner.name}[/bold red] is warp out...")
                        async for result, message in arbiter_runner.start_phase(WarpInPhase.DISAPPEARANCE):                        
                            match result:
                                case WarpInTaskResult.SUCCESS:
                                    # Danimoth's warp-out completed.
                                    console.print(f"[bold green]{arbiter_runner.name}[/bold green]'s warp-out [bold green]Completed[bold green].")
                                    break
                                case WarpInTaskResult.WARNING:
                                    console.log(f"[bold yellow]{arbiter_runner.name}[/bold yellow]'s warp-out catch warning {message}")
                                case WarpInTaskResult.FAIL:
                                    console.log(f"[bold red]{arbiter_runner.name}[/bold red]'s warp-out catch fail {message}")
                                    break
                                    # check aribter runner is clean up
            except Exception as e:
                # start_phase에서 발생한 예외를 처리한다.
                console.print(f"[bold red]An error occurred when loading arbiter[/bold red] {e}")
        
        
        ################## RUN #####################
        system_queue: asyncio.Queue[Annotated[str, "command"]] = asyncio.Queue()
         
        """
        Read the config file.
        """
        # It need to add when use cli command
        # sys.path.insert(0, os.getcwd())

        arbiter_setting, is_arbiter_setting = get_arbiter_setting(CONFIG_FILE)
        if not is_arbiter_setting:
            create_config(arbiter_setting)
        config = read_config(arbiter_setting)

        
        """
        Set the config to the app.
        runner, worker, api app shared the same config.
        # CHECK 
        """
        app.setup(config)
        
        try:
            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, lambda s, f: shutdown_signal_handler(system_queue))
            signal.signal(signal.SIGTERM, lambda s, f: shutdown_signal_handler(system_queue))
            asyncio.run(arbiter_run(app, config, system_queue))
        except SystemExit as e:
            console.print(f"SystemExit caught in main: {e.code}")
        except KeyboardInterrupt:
            console.print("KeyboardInterrupt caught in main")
        except Exception as e:
            console.print(f"Unhandled exception in main: {e}")
        
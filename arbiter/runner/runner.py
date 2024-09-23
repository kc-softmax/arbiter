import signal
import typer
import asyncio
from rich.console import Console
from typing_extensions import Annotated
from arbiter.enums import (
    WarpInPhase,
    WarpInTaskResult,
)
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
        coroutine_event = asyncio.Event()
        def shutdown_signal_handler(coroutine_event: asyncio.Event):
            coroutine_event.set()
            # asyncio.ensure_future(async_shutdown_signal_handler(coroutine_event))

        # async def async_shutdown_signal_handler(coroutine_event: asyncio.Event):
        #     coroutine_event.set()

        async def arbiter_run(
            arbiter_app: ArbiterApp,
            system_queue: asyncio.Queue[Annotated[str, "command"]],
            coroutine_event: asyncio.Event,
        ):
            """
            Get the configure parameters from config file.
            """
            
            try:
                async with arbiter_app.warp_in(
                    system_queue=system_queue,
                ) as arbiter_runner:
                    try:
                        console.print(f"[bold green]Warp In [bold yellow]Arbiter[/bold yellow] [bold green]{arbiter_runner.name}...[/bold green]")
                        
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

                        """asyncio.Event
                        It used to share the state of each coroutine.
                        1. Event flag will change when occur keyboard interrupt signal
                        2. Event wait until called event set
                        """
                        await coroutine_event.wait()

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
        try:
            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, lambda s, f: shutdown_signal_handler(coroutine_event))
            signal.signal(signal.SIGTERM, lambda s, f: shutdown_signal_handler(coroutine_event))
            asyncio.run(arbiter_run(app, system_queue, coroutine_event))
        except SystemExit as e:
            console.print(f"SystemExit caught in main: {e.code}")
        except KeyboardInterrupt:
            console.print("KeyboardInterrupt caught in main")
        except Exception as e:
            console.print(f"Unhandled exception in main: {e}")
        
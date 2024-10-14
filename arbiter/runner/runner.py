import signal
import asyncio
from rich.console import Console
from arbiter.enums import (
    WarpInPhase,
    WarpInTaskResult,
)
from arbiter.runner.console import arbiter_console_context
from arbiter.configs import ArbiterConfig,BrokerConfig
from arbiter.node import ArbiterNode
from arbiter.utils import wait_until
from arbiter import Arbiter

console = Console()

class ArbiterRunner:
        
    @staticmethod
    def run(
        app: ArbiterNode,
        broker_config: BrokerConfig,
        arbiter_config: ArbiterConfig = ArbiterConfig(),
        repl: bool = False,
    ):        
        # some validation?        
        arbiter = Arbiter(
            arbiter_config,
            broker_config,
        )        
        # gateway validation with system?        
        app.setup(arbiter)
        

        async def arbiter_run(
            arbiter_app: ArbiterNode,
        ):
            """
            Get the configure parameters from config file.
            """
            def shutdown_signal_handler():
                shutdown_event.set()

            shutdown_event = asyncio.Event()
            
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, shutdown_signal_handler)

            try:
                async with arbiter_app.warp_in(
                    shutdown_event
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
                                case WarpInTaskResult.INFO:
                                    console.print(f"[bold green]{arbiter_runner.name}[/bold green] [white]{message}[/white]")
                                case WarpInTaskResult.WARNING:
                                    console.print(f"[bold yellow]{arbiter_runner.name}[/bold yellow] [bold blue]{message}[/bold blue].")
                                case WarpInTaskResult.FAIL:
                                    raise Exception(message)

                        """asyncio.Event
                        It used to share the state of each coroutine.
                        1. Event flag will change when occur keyboard interrupt signal
                        2. Event wait until called event set
                        """
                        """
                            # (Press CTRL+C to quit)                            
                        """
                        # launch gateway first
                        if arbiter_runner.gateway_server:
                            gateway_task = arbiter_runner.start_gateway(shutdown_event)
                            if not await wait_until(lambda: arbiter_runner.gateway_server.started, timeout=5.0):
                                raise Exception("Gateway server is not started.")
                        else:
                            gateway_task = None
                        
                        if repl:
                            async with arbiter_console_context(arbiter_runner, shutdown_event) as interact_task:
                                # print("Waiting for interact to complete...")
                                await interact_task
                                if arbiter_runner.gateway_server:
                                    arbiter_runner.gateway_server.should_exit = True
                                    await asyncio.gather(gateway_task, shutdown_event.wait())
                                else:
                                    await asyncio.gather(shutdown_event.wait())
                        else:
                            if arbiter_runner.gateway_server:
                                await asyncio.gather(gateway_task, shutdown_event.wait())
                            else:
                                console.print(f"[bold white]Press [red]CTRL + C[/red] to quit[/bold white]")
                                await asyncio.gather(shutdown_event.wait())

                    except Exception as e:
                        # arbiter 를 소환 혹은 실행하는 도중 예외가 발생하면 처리한다.
                        console.print(f"[bold red]An error occurred when warp-in..[/bold red] {e}")
                    finally:
                        console.print(f"[bold red]{arbiter_runner.name}[/bold red] is warp out...")
                        async for result, message in arbiter_runner.start_phase(WarpInPhase.DISAPPEARANCE):                        
                            match result:
                                case WarpInTaskResult.SUCCESS:
                                    # console.print(f"[bold green]{arbiter_runner.name}[/bold green]'s warp-out [bold green]Completed[bold green].")
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
        """
        Read the config file.
        """
        try:
            # Register signal handlers for graceful shutdown
            asyncio.run(arbiter_run(app))
        except SystemExit as e:
            console.print(f"SystemExit caught in main: {e.code}")
        except KeyboardInterrupt:
            console.print("KeyboardInterrupt caught in main")
        except Exception as e:
            console.print(f"Unhandled exception in main: {e}")
        
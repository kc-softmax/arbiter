import signal
import asyncio
from typing import Any
from rich.console import Console
from watchfiles import awatch
from arbiter.enums import (
    WarpInPhase,
    WarpInTaskResult,
)
from arbiter.node import ArbiterNode
from arbiter.runner.console import arbiter_console_context
from arbiter.runner.utils import get_app, get_reload_dirs, get_module_path_from_main

console = Console()

class ArbiterRunner:


    # @classmethod
    # def signal_handler(cls, signum, frame):
    #     cls.shutdown_event.set()
    @classmethod
    async def arbiter_run(
        cls, 
        arbiter_node: ArbiterNode,
        interept_event: asyncio.Event
    ):
        try:
            async with arbiter_node.warp_in(
                interept_event
            ) as node:
                try:
                    console.print(f"[bold green]Warp In [bold yellow]Arbiter[/bold yellow] [bold green]{node.name}...[/bold green]")
                    
                    async for result, message in node.start_phase(WarpInPhase.PREPARATION):
                        match result:
                            # Danimoth is the warp-in master.
                            case WarpInTaskResult.SUCCESS:
                                console.print(f"[bold green]{node.name}[/bold green] [bold yellow]{message}[/bold yellow].")
                                break
                            case WarpInTaskResult.FAIL:
                                raise Exception(message)

                    async for result, message in node.start_phase(WarpInPhase.INITIATION):
                        match result:
                            case WarpInTaskResult.SUCCESS:
                                console.print(f"[bold green]{node.name}[/bold green] [bold yellow]{message}[/bold yellow].")
                                break
                            case WarpInTaskResult.INFO:
                                console.print(f"[bold green]{node.name}[/bold green] [white]{message}[/white]")
                            case WarpInTaskResult.WARNING:
                                console.print(f"[bold yellow]{node.name}[/bold yellow] [bold blue]{message}[/bold blue].")
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
                    # loop until shutdown_event is set
                    await interept_event.wait()

                except Exception as e:
                    # arbiter 를 소환 혹은 실행하는 도중 예외가 발생하면 처리한다.
                    console.print(f"[bold red]An error occurred when warp-in..[/bold red] {e}")
                finally:
                    console.print(f"[bold red]{node.name}[/bold red] is warp out...")
                    async for result, message in node.start_phase(WarpInPhase.DISAPPEARANCE):                        
                        match result:
                            case WarpInTaskResult.SUCCESS:
                                console.print(f"[bold green]{node.name}[/bold green]'s warp-out [bold green]Completed[bold green].")
                                break
                            case WarpInTaskResult.WARNING:
                                console.log(f"[bold yellow]{node.name}[/bold yellow]'s warp-out catch warning {message}")
                            case WarpInTaskResult.FAIL:
                                console.log(f"[bold red]{node.name}[/bold red]'s warp-out catch fail {message}")
                                break
                                # check aribter runner is clean up
        except Exception as e:
            # start_phase에서 발생한 예외를 처리한다.
            console.print(f"[bold red]An error occurred when loading arbiter[/bold red] {e}")
    # @classmethod
    # def runner(
    #     cls,
    #     module: str,
    #     app_name: str,
    # ) -> Any:
    #     # 자식 프로세스에서 키보드 인터럽트 (SIGINT)를 무시하도록 설정
    #     signal.signal(signal.SIGINT, signal.SIG_IGN)
    #     app = get_app(module, app_name)

    #     if isinstance(app, type):
    #         app = app()

    #     assert isinstance(app, ArbiterNode), f"instance must be ArbiterNode, but {module} is {type(app)}"
    #     try:
    #         asyncio.run(cls.arbiter_run(app, shutdown_event))
    #     except asyncio.CancelledError:
    #         pass    
    #     except Exception as e:
    #         console.print(f"An error occurred when running arbiter: {e}")
        
    @classmethod
    async def watch_and_restart(
        cls,
        app: ArbiterNode,
        module: str,
    ):
        arbiter_task: asyncio.Task = None
        reload_dirs = get_reload_dirs(module)  
        try:            
            interept_event = asyncio.Event()
            shutdown_event = asyncio.Event()
            
            def signal_handler(signum, frame):
                interept_event.set()
                shutdown_event.set()
                
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # 최초 실행
            arbiter_task = asyncio.create_task(cls.arbiter_run(app, interept_event))
            
            async for changes in awatch(*reload_dirs, stop_event=shutdown_event):
                """
                    체인지가 아니라, app이 스스로 종료되었을 때 어떻게 알 수 있을까?
                """
                interept_event.set()
                await arbiter_task
                interept_event.clear()
                arbiter_task = asyncio.create_task(cls.arbiter_run(app, interept_event))
            
            await arbiter_task
            
        except KeyboardInterrupt:
            print("KeyboardInterrupt caught in watch_and_restart")
            # Keyboard interrupt signal -> exit by reloading
            pass
        except Exception as e:
            console.print(f"An error occurred when watching and restarting: {e}")
            
    @classmethod
    def run(
        cls,
        app: ArbiterNode | str,
        reload: bool = False,
    ):
        if isinstance(app, str):
            """
            if app is string, it means that module path.
                and then, import the module from the module path.
            if reload is True, reload dir set below example.
                a. module path is tests.app:app, reload dir is tests/
                b. module path is app:app, reload dir is ./
            """
            module, _, app_name = app.partition(":")
            assert module, "The module path must be in format <module>:<attribute>."
            app = get_app(module, app_name)
            if isinstance(app, type):
                app = app()
            assert isinstance(app, ArbiterNode), f"instance must be ArbiterNode, but {module} is {type(app)}"
        else:
            module = get_module_path_from_main()
            app_name = None
        ################## RUN #####################        
        try:
            # if not reload:
            #     process = Process(
            #         target=cls.runner, 
            #         args=(cls.shutdown_event, module, app_name)
            #     )
            #     process.start()
            #     process.join()
            # else:
            asyncio.run(cls.watch_and_restart(app, module))
        except SystemExit as e:
            console.print(f"SystemExit caught in main: {e.code}")
        except KeyboardInterrupt:
            console.print("KeyboardInterrupt caught in main")
        except Exception as e:
            console.print(f"Unhandled exception in main: {e}")


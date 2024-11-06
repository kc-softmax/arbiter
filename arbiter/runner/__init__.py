import signal
import asyncio
from typing import Any
from rich.console import Console
from multiprocessing import Event, Process
from multiprocessing.synchronize import Event as MPEvent
from watchfiles import watch
from arbiter.enums import (
    WarpInPhase,
    WarpInTaskResult,
)
from arbiter.node import ArbiterNode
from arbiter.runner.console import arbiter_console_context
from arbiter.runner.utils import get_app, get_reload_dirs, get_module_path_from_main

console = Console()

class ArbiterRunner:

    shutdown_event = Event()

    @classmethod
    def signal_handler(cls, signum, frame):
        cls.shutdown_event.set()

    @classmethod
    async def arbiter_run(
        cls,
        arbiter_app: ArbiterNode,
        shutdown_event: MPEvent,
        repl: bool,
    ):
        """
        Get the configure parameters from config file.
        """
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
                                # console.print(f"[bold green]{arbiter_runner.name}[/bold green] [bold yellow]{arbiter_runner.node_id}[/bold yellow].")
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
                    
                    if repl:
                        async with arbiter_console_context(
                            arbiter_runner, 
                            shutdown_event
                        ) as repl_task:
                            print("Waiting for interact to complete...")
                            await repl_task
                    else:
                        console.print(f"[bold white]Press [red]CTRL + C[/red] to quit[/bold white]")
                    
                    # loop until shutdown_event is set
                    await arbiter_runner.is_alive_event.wait()

                except Exception as e:
                    # arbiter 를 소환 혹은 실행하는 도중 예외가 발생하면 처리한다.
                    console.print(f"[bold red]An error occurred when warp-in..[/bold red] {e}")
                finally:
                    console.print(f"[bold red]{arbiter_runner.name}[/bold red] is warp out...")
                    async for result, message in arbiter_runner.start_phase(WarpInPhase.DISAPPEARANCE):                        
                        match result:
                            case WarpInTaskResult.SUCCESS:
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
         
    @classmethod
    def runner(
        cls,
        shutdown_event: MPEvent,
        module: str,
        app_name: str,
        repl: bool
    ) -> Any:
        # 자식 프로세스에서 키보드 인터럽트 (SIGINT)를 무시하도록 설정
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        app = get_app(module, app_name)

        if isinstance(app, type):
            app = app()

        assert isinstance(app, ArbiterNode), f"instance must be ArbiterNode, but {module} is {type(app)}"
        try:
            asyncio.run(cls.arbiter_run(app, shutdown_event, repl))
        except asyncio.CancelledError:
            pass    
        except Exception as e:
            console.print(f"An error occurred when running arbiter: {e}")
        
    @classmethod
    async def watch_and_restart(
        cls,
        module: str,
        app_name: str,
        repl: bool = False,
    ):
        reload_dirs = get_reload_dirs(module)
        
        try:
            # 최초 실행
            process = Process(
                target=cls.runner,
                args=(cls.shutdown_event, module, app_name, repl)
            )
            process.start()
            for changes in watch(*reload_dirs, stop_event=cls.shutdown_event):
                """
                    체인지가 아니라, app이 스스로 종료되었을 때 어떻게 알 수 있을까?
                """
                cls.shutdown_event.set()
                process.join()
                process = Process(
                    target=cls.runner, 
                    args=(cls.shutdown_event, module, app_name, repl)
                )
                process.start()
                cls.shutdown_event.clear()

        except KeyboardInterrupt:
            # Keyboard interrupt signal -> exit by reloading
            pass
        except Exception as e:
            console.print(f"An error occurred when watching and restarting: {e}")
            
    @classmethod
    def run(
        cls,
        app: ArbiterNode | str,
        # repl: bool = False,
        reload: bool = False,
    ):
        repl = False
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
        else:
            module = get_module_path_from_main()
            app_name = None
        ################## RUN #####################        
        try:
            # add signal handler to main process        
            signal.signal(signal.SIGINT, cls.signal_handler)
            signal.signal(signal.SIGTERM, cls.signal_handler)

            if not reload:
                process = Process(
                    target=cls.runner, 
                    args=(cls.shutdown_event, module, app_name, repl)
                )
                process.start()
                process.join()
            else:
                asyncio.run(cls.watch_and_restart(module, app_name, repl))
        except SystemExit as e:
            console.print(f"SystemExit caught in main: {e.code}")
        except KeyboardInterrupt:
            console.print("KeyboardInterrupt caught in main")
        except Exception as e:
            console.print(f"Unhandled exception in main: {e}")


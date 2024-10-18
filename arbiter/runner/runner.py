import importlib
import os
from pathlib import Path
import signal
import asyncio
from typing import Any
from rich.console import Console
from watchfiles import awatch
from arbiter.enums import (
    WarpInPhase,
    WarpInTaskResult,
)
from arbiter.runner.console import arbiter_console_context
from arbiter.node import ArbiterNode
from arbiter.utils import wait_until

console = Console()

def get_app(module: str, app: str) -> Any:
    try:
        module = importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if exc.name != module:
            raise exc from None
        message = 'Could not import module "{module}".'
        raise Exception(f"Could not import module {module}")

    instance = module
    try:
        instance = getattr(instance, app)
    except AttributeError:
        raise Exception(f"app name {app} is not found in module {module}")

    return instance

def get_reload_dirs(module: str = None) -> list[Path]:
    if not module:
        reload_dirs = [Path(os.getcwd())]
    else:
        reload_dir = module.split(".")
        reload_dir.pop()
        reload_dir = f"{os.getcwd()}/" + ".".join(reload_dir)
        reload_dirs = [Path(reload_dir)]
    return reload_dirs

class ArbiterRunner:
        
    @staticmethod
    def run(
        app: ArbiterNode | str,
        repl: bool = False,
        reload: bool = False,
    ):        
        async def arbiter_run(
            arbiter_app: ArbiterNode,
        ):
            """
            Get the configure parameters from config file.
            """
            def shutdown_signal_handler():
                shutdown_event.set()
                app.internal_shutdown_event.set()
                
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

                        async for result, message in arbiter_runner.start_phase(WarpInPhase.MATERIALIZATION):
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

        async def watch_and_restart(app: ArbiterNode, reload_dirs: list[Path]):
            task: asyncio.Task = None
            try:
                # 최초 실행
                task = asyncio.create_task(arbiter_run(app))
                async for changes in awatch(*reload_dirs, stop_event=app.internal_shutdown_event):
                    """
                        체인지가 아니라, app이 스스로 종료되었을 때 어떻게 알 수 있을까?
                    """
                    print(f"Detected changes: {changes}")
                    shutdown_event.set()
                    # 기존 작업 중단
                    if task:
                        try:
                            await asyncio.wait_for(task, timeout=10)
                        except asyncio.TimeoutError:
                            print("Task timeout")
                        except Exception as e:
                            print(f"Task exception: {e}")
                    # 재시작
                    shutdown_event.clear()
                    task = asyncio.create_task(arbiter_run(app))
                    print("new task")
            except KeyboardInterrupt:
                # Keyboard interrupt signal -> exit by reloading
                pass
            finally:
                # Graceful shutdown
                if task:
                    shutdown_event.set()
                    try:
                        await asyncio.wait_for(task, timeout=10)
                    except asyncio.TimeoutError:
                        print("Final Task timeout")
                    except Exception as e:
                        print(f"Final Task exception: {e}")
                    
        if isinstance(app, str):
            """
            if app is string, it means that module path.
                and then, import the module from the module path.
            if reload is True, reload dir set below example.
                a. module path is tests.app:app, reload dir is tests/
                b. module path is app:app, reload dir is ./
            """
            module, _, app = app.partition(":")
            assert module and app, "The module path must be in format <module>:<attribute>."
            app = get_app(module, app)
            reload_dirs = get_reload_dirs(module)
        else:
            reload_dirs = get_reload_dirs()
                    
        assert isinstance(app, ArbiterNode), f"instance must be ArbiterNode, but {module} is {type(app)}"
        
        ################## RUN #####################
        
        shutdown_event = asyncio.Event()
        
        try:
            if not reload:
                asyncio.run(arbiter_run(app))
            else:
                asyncio.run(watch_and_restart(app, reload_dirs))
        except SystemExit as e:
            console.print(f"SystemExit caught in main: {e.code}")
        except KeyboardInterrupt:
            console.print("KeyboardInterrupt caught in main")
        except Exception as e:
            console.print(f"Unhandled exception in main: {e}")
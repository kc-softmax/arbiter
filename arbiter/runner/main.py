import pytest
import typer
from uvicorn.importer import import_from_string
# from arbiter.runner.commands.build import app as build_app
from arbiter.constants import CONFIG_FILE
from arbiter import ArbiterRunner, ArbiterNode
from arbiter.configs import NatsBrokerConfig, ArbiterNodeConfig
from arbiter.runner.runner import ArbiterRunner
from arbiter.node import ArbiterNode
from arbiter.runner.utils import create_config
from arbiter.utils import get_arbiter_setting, read_config

app = typer.Typer()
# app.add_typer(
#     build_app,
#     name="build",
#     rich_help_panel="build environment",
#     help="Configure build environment for deploying service")

@app.command(help="run arbiter rel")
def repl(
    name: str = typer.Option(
        "Danimoth", "--name", help="Name of the arbiter to run."),
):
    # main:app 과 같은 느낌으로 가져오는거니까 config이 필요 없다.
    # 하지만 repl이기 때문에 app 변수를 가져와야 한다.

    ArbiterRunner.run(
        ArbiterNode(
            config=ArbiterNodeConfig(system_timeout=0),
            gateway=None,
            ),
        broker_config=NatsBrokerConfig(),
        repl=True)
    

@app.command(help="run arbiter service")
def dev(
    # not optional
    module: str = typer.Argument(
        ...,
        help="The module path to the arbiter service."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for code changes."),
    log_level: str = typer.Option(
        "info", "--log-level", help="Log level for arbiter.")
):
    # main:app 과 같은 느낌으로 가져오는거니까 config이 필요 없지
    """
    Set the config to the app.
    runner, worker, api app shared the same config.
    # CHECK 
    """
    instance = import_from_string(module)
    
    print(instance)
    # 서비스를 내가 찾아서 추가해야 한다.
    # app.setup(config)
    # run에는 config을 이용해서 한다.
    # app = ArbiterNode()
    # # find services in ./services folder
    # """
    #     현재 폴더에 있는 모든 서비스를 추가한다.
    # """
    # # service를 추가해야 하나?
    # # services 폴더에 있는 모든 service를 추가해야 하자
    # # aribter add service?
    # ArbiterRunner.run(
    #     app=app,
    #     name=name,
    #     reload=reload,
    #     log_level=log_level
    # )


@app.command(help="run arbiter testcase")
def test():
    import asyncio
    import logging
    import timeit
    DEFAULT_TIMEOUT = 30
    logging.basicConfig(level=logging.INFO, format='ARBITER - TEST %(asctime)s - %(levelname)s - %(message)s')

    logger = logging.getLogger()
    running_state: dict[str, bool] = {
        "arbiter": False,
        "pytest": False,
    }

    async def run_arbiter():        
        from arbiter.enums import (
            WarpInPhase,
            WarpInTaskResult,
        )
        from tests.service import TestService, TestException
        from arbiter.gateway import ArbiterGatewayService
        
        app = ArbiterNode()
        app.add_service(ArbiterGatewayService())
        app.add_service(TestService())
        # app.add_service(TestException())

        async with app.warp_in(system_queue=asyncio.Queue()) as arbiter_runner:
            try:
                async for result, message in arbiter_runner.start_phase(WarpInPhase.PREPARATION):
                    match result:
                        # Danimoth is the warp-in master.
                        case WarpInTaskResult.SUCCESS:
                            logger.info("PREPARATION success")
                            break
                        case WarpInTaskResult.FAIL:
                            raise Exception(message)

                async for result, message in arbiter_runner.start_phase(WarpInPhase.INITIATION):
                    match result:
                        case WarpInTaskResult.SUCCESS:
                            logger.info("INITIATION success")
                            break
                        case WarpInTaskResult.WARNING:
                            logger.warning("INITIATION warning")
                        case WarpInTaskResult.FAIL:
                            raise Exception(message)

                logger.info("ARBITER started")
                running_state["arbiter"] = True
                # pytest가 끝날때까지 기다린다
                start = timeit.default_timer()
                while not running_state["pytest"]:
                    await asyncio.sleep(0.1)
                    # 30초 이상 걸리면 종료
                    if timeit.default_timer() - start > DEFAULT_TIMEOUT:
                        raise TimeoutError("time over")
            except Exception as e:
                logger.error(e)
            finally:
                async for result, message in arbiter_runner.start_phase(WarpInPhase.DISAPPEARANCE):                        
                    match result:
                        case WarpInTaskResult.SUCCESS:
                            # Danimoth's warp-out completed.
                            logger.info("DISAPPEARANCE success")
                            break
                        case WarpInTaskResult.WARNING:
                            logger.warning("DISAPPEARANCE warning")
                        case WarpInTaskResult.FAIL:
                            logger.error("DISAPPEARANCE fail")
                            break
                logger.info("ARBITER closed")

    async def run_pytest(arbiter_task: asyncio.Task):
        try:
            # arbiter가 실행될때까지 기다린다
            start = timeit.default_timer()
            while not running_state["arbiter"]:
                await asyncio.sleep(0.1)
                # 30초 이상 걸리면 종료
                if timeit.default_timer() - start > DEFAULT_TIMEOUT:
                    raise TimeoutError("time over")
            if arbiter_task.done():
                raise Exception("Error with something")
            command = "pytest"
            proc = await asyncio.subprocess.create_subprocess_shell(cmd=command, shell=True)
            await proc.communicate()
            logger.info("PYTEST finished")
            running_state["pytest"] = True
        except Exception as e:
            logger.error(e)

    async def main():
        arbiter_task = asyncio.create_task(run_arbiter())
        pytest_task = asyncio.create_task(run_pytest(arbiter_task))
        try:
            _ = await asyncio.wait(
                [arbiter_task, pytest_task],
                return_when=asyncio.ALL_COMPLETED
            )
        except Exception as e:
            logger.error(e)

    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    app()

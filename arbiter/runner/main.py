import typer
# from arbiter.runner.commands.build import app as build_app
from arbiter.runner.runner import ArbiterRunner
from arbiter.app import ArbiterApp

app = typer.Typer()
# app.add_typer(
#     build_app,
#     name="build",
#     rich_help_panel="build environment",
#     help="Configure build environment for deploying service")


@app.command(help="run arbiter service")
def run(
    name: str = typer.Option(
        "Danimoth", "--name", help="Name of the arbiter to run."),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for code changes."),
    log_level: str = typer.Option(
        "info", "--log-level", help="Log level for arbiter.")
):
    app = ArbiterApp()
    ArbiterRunner.run(
        app=app,
        name=name,
        reload=reload,
        log_level=log_level
    )


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
        from arbiter.utils import (
            check_redis_running,
            read_config,
            get_arbiter_setting,
        )
        from arbiter.runner.utils import (
            create_config,
        )
        from arbiter.constants import CONFIG_FILE
        from tests.test_service import TestService
        app = ArbiterApp()
        app.add_service(TestService)
        arbiter_setting, is_arbiter_setting = get_arbiter_setting(CONFIG_FILE)
        if not is_arbiter_setting:
            create_config(arbiter_setting)
        config = read_config(arbiter_setting)

        app.setup(config)

        if not await check_redis_running(
            host=config.get("broker", "host"),
            port=config.getint("broker", "port"),
            password=config.get("broker", "password"),
        ):
            logger.error("REDIS FAIL TO START")
            running_state["arbiter"] = True
            return

        async with app.warp_in(system_queue=asyncio.Queue()) as arbiter_runner:
            try:
                if arbiter_runner.arbiter_node.is_master:
                    logger.info("master")
                else:
                    logger.info("slave")

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

                async for result, message in arbiter_runner.start_phase(WarpInPhase.MATERIALIZATION):
                    match result:
                        case WarpInTaskResult.SUCCESS:
                            logger.info("MATERIALIZATION success")
                            break
                        case WarpInTaskResult.WARNING:
                            logger.warning("MATERIALIZATION warning")
                        case WarpInTaskResult.FAIL:
                            raise Exception(message)

                logger.info("ARBITER started")
                running_state["arbiter"] = True
                # pytest가 끝날때까지 기다린다
                start = timeit.default_timer()
                while not running_state["pytest"]:
                    await asyncio.sleep(0.1)
                    # 5초 이상 걸리면 종료
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

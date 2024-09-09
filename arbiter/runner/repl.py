import code
import sys
import asyncio
from arbiter import Arbiter
from arbiter.data.models import ArbiterTaskModel


class ArbiterConsole(code.InteractiveConsole):
    
    def __init__(
        self,
        arbiter: Arbiter
    ):
        self.arbiter = arbiter
        super().__init__()
    
    def interact(self, banner=None):
        # 프롬프트를 빈 문자열로 설정
        sys.ps1 = 'arbiter $ '
        sys.ps2 = ''
        super().interact(banner)

    def runsource(self, source, filename="<input>", symbol="single"):
        # 특정 코드가 실행될 때만 특별한 처리를 할 수 있음
        if source.strip().startswith("arbiter "):
            return asyncio.run(self.run_arbiter_task(source.strip()))
        if source == "exit()":
            print("Exiting the REPL!")
            return True
        return super().runsource(source, filename, symbol)
    
    async def run_arbiter_task(self, source):
        try:
            print(f"Running arbiter task...{source}")
            results = await self.arbiter.async_task(
                "test_service_two_params",
                5,
                5
            )
            print(results)
            # if task_models := await self.arbiter.search_data(ArbiterTaskModel):
            #     for task_model in task_models:
            #         print(task_model)
            # # 비동기 코드를 실행하기 위한 wrapper
            # exec(f"async def __async_exec():\n{source}")
            # result = await locals()['__async_exec']()
            # if result is not None:
            #     print(result)
        except Exception as e:
            print(f"Error in run_arbiter_task: {e}")
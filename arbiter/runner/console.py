import code
import sys
import asyncio
from arbiter import Arbiter
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


class ArbiterConsole(code.InteractiveConsole):
    
    def __init__(
        self,
        arbiter: Arbiter,
        shutdown_event: asyncio.Event,
    ):
        self.arbiter = arbiter
        self.shutdown_event = shutdown_event
        self.session = PromptSession()
        super().__init__()


    async def check_shutdown_event(self):
        # shutdown_event가 set되면 session의 prompt를 강제 종료
        await self.shutdown_event.wait()
        if self.session.app.is_running:
            self.session.app.exit()  # 이 부분이 session.prompt() 대기를 깨울 수 있음

    def interact(self, banner=None):
        # 프롬프트를 빈 문자열로 설정
        sys.ps1 = 'arbiter $ '
        sys.ps2 = ''
        super().interact(banner)

    def raw_input(self, prompt=""):
        with patch_stdout():
            print(prompt, end='', flush=True)            
            while not self.shutdown_event.is_set():
                try:
                    user_input = self.session.prompt('')
                    if user_input is None:
                        raise EOFError
                    return user_input
                except EOFError:
                    raise EOFError
        raise EOFError
        
    def runsource(self, source, filename="<input>", symbol="single"):
        # 특정 코드가 실행될 때만 특별한 처리를 할 수 있음
        if source.strip().startswith("arbiter "):
            return asyncio.run(self.run_arbiter_task(source.strip()))
        if source == "exit()":
            self.shutdown_event.set()
            return True
        return super().runsource(source, filename, symbol)
    
    async def run_arbiter_task(self, source):
        try:
            print(f"Running arbiter task...{source}")
        except Exception as e:
            print(f"Error in run_arbiter_task: {e}")
            
@asynccontextmanager
async def arbiter_console_context(
    arbiter: Arbiter,
    shutdown_event: asyncio.Event,
):
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor()
    console = ArbiterConsole(arbiter, shutdown_event)
    try:
        asyncio.create_task(console.check_shutdown_event())
        # Run the console.interact method in a separate thread
        interact_task = loop.run_in_executor(executor, console.interact)
        yield interact_task  # Provide the console instance within the context
        # Wait for interact to complete
    finally:
        # Clean up the executor
        executor.shutdown(wait=True)
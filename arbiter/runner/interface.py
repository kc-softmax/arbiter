import asyncio
import sys
import termios
from contextlib import asynccontextmanager, suppress
from typing import Annotated
from asyncio import StreamReader
from rich.console import Console
console = Console()

class TerminalInterface:
    def __init__(
        self,
        system_queue: asyncio.Queue[Annotated[str, "command"]],
    ):
        self.system_queue = system_queue
    
    @asynccontextmanager
    async def raw_mode(self, file):
        """Enter raw mode for terminal input."""
        old_attrs = termios.tcgetattr(file.fileno())
        new_attrs = old_attrs[:]
        new_attrs[3] = new_attrs[3] & ~(termios.ECHO | termios.ICANON)
        try:
            termios.tcsetattr(file.fileno(), termios.TCSADRAIN, new_attrs)
            yield
        finally:
            termios.tcsetattr(file.fileno(), termios.TCSADRAIN, old_attrs)
    
    async def connect_stdin_stdout(self) -> StreamReader:
        """Stream stdin as async."""
        _loop = asyncio.get_event_loop()
        reader = StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await _loop.connect_read_pipe(lambda: protocol, sys.stdin)
        return reader
    
    @asynccontextmanager
    async def interact(self):
        """Interact with the system via the system queue."""
        async def read_input(reader: StreamReader):
            while True:
                input = await reader.read(100)
                input = input.decode().upper().strip()
                await self.system_queue.put(input)
        
        reader = await self.connect_stdin_stdout()
        task = asyncio.create_task(read_input(reader))
        try:
            yield self.system_queue
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def __aenter__(self):
        """Enter the async context manager."""
        self.raw_mode_manager = self.raw_mode(sys.stdin)
        await self.raw_mode_manager.__aenter__()
        self.interact_manager = self.interact()
        return await self.interact_manager.__aenter__()

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Exit the async context manager."""
        await self.interact_manager.__aexit__(exc_type, exc_value, traceback)
        await self.raw_mode_manager.__aexit__(exc_type, exc_value, traceback)
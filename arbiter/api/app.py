from arbiter.api import ArbiterApiApp

from uvicorn.server import Server
from uvicorn.config import Config


class ArbiterUvicornWorker:

    @staticmethod
    async def run(app: ArbiterApiApp, host: str, port: int, log_level: str = 'info'):
        config = Config(app, host=host, port=port, log_level=log_level)
        server = Server(config)
        await server.serve()

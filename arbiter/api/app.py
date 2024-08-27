import json
import os
import uuid

from arbiter.api import ArbiterApiApp
from arbiter.runner.utils import create_config
from arbiter.utils import (
    get_arbiter_setting,
    read_config,
)
from arbiter.constants import CONFIG_FILE

from uvicorn.server import Server
from uvicorn.config import Config


class ArbiterUvicornWorker:

    @staticmethod
    async def run(app: ArbiterApiApp, unique_id: str | None = None):
        if unique_id is None:
            unique_id = uuid.uuid4().hex

        arbiter_setting, is_arbiter_setting = get_arbiter_setting(CONFIG_FILE)
        if not is_arbiter_setting:
            create_config(arbiter_setting)
        config = read_config(arbiter_setting)

        host = config.get("server", "host", fallback="localhost")
        port = config.get("server", "port", fallback="8080")
        log_level = config.get("server", "log_level", fallback="error")
        broker_config = dict(config['broker'])
        server_config = dict(config['server'])
        os.environ["NODE_ID"] = unique_id
        os.environ["BROKER_CONFIG"] = json.dumps(broker_config)
        os.environ["SERVER_CONFIG"] = json.dumps(server_config)

        config = Config(app=app, host=host, port=port, log_level=log_level)
        server = Server(config)
        await server.serve()

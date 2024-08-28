import json
import os
from .app import ArbiterApiApp
from .worker import ArbiterUvicornWorker

def get_app() -> ArbiterApiApp:    
    node_id = os.getenv("NODE_ID", "")
    broker_config = os.getenv("BROKER_CONFIG", {})
    server_config = os.getenv("SERVER_CONFIG", {})
    assert node_id, "NODE_ID is not set"
    assert broker_config, "BROKER_CONFIG is not set"
    assert server_config, "SERVER_CONFIG is not set"
    broker_config = json.loads(broker_config)
    server_config = json.loads(server_config)
    assert isinstance(broker_config, dict), "BROKER_CONFIG is not valid"
    assert isinstance(server_config, dict), "SERVER_CONFIG is not valid"
    return ArbiterApiApp(
        node_id=node_id,
        broker_host=broker_config.get("host", "localhost"),
        broker_port=broker_config.get("port", 6379),
        broker_password=broker_config.get("password", None),
        allow_origins=server_config.get("allow_origins", "*"),
        allow_methods=server_config.get("allow_methods", "*"),
        allow_headers=server_config.get("allow_headers", "*"),
        allow_credentials=server_config.get("allow_credentials", True),
    )
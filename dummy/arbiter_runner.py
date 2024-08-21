from . import Arbiter

import uvicorn


class ArbiterRunner:
    def __init__(self) -> None:
        pass

    @classmethod
    def run(cls, app: Arbiter, host: str, port: int, reload: bool = False, log_level: str = "info"):
        uvicorn.run(app, host=host, port=port, reload=reload, log_level=log_level)        

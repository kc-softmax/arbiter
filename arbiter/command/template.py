import os

PROJECT_NAME  = "arbiter_server"

MAIN_FILE = "main.py"
REPOSITORY_FILE = "repository.py"
MODEL_FILE = "model.py"
ENGINE_FILE = "engine.py"
CONFIG_FILE = "arbiter.setting.ini"

ENGINE_CONTENTS = """
from arbiter.api.live.engine import LiveAsyncEngine

class MyLiveEngine(LiveAsyncEngine):
    # Writing your code
    pass
"""

MAIN_CONTENTS = """
from fastapi import Query,WebSocket

# from arbiter.api.dependencies import unit_of_work # Use this when you need to work with databases.
from arbiter.api.live.service import LiveService
from arbiter.api.main import app

from .engine import MyLiveEngine

live_service = LiveService(MyLiveEngine())

# Can add the handler for LiveConnectionEvent
# @live_service.on_event(LiveConnectionEvent.VALIDATE)
# pass

# If you need, set the custom router
# router = APIRouter(
#    prefix="/my_service",
#)

@app.websocket("/ws")
async def connect_live_service(websocket: WebSocket, token: str = Query()):
    async with live_service.connect(websocket, token) as [user_id, user_name]:
        await live_service.publish_to_engine(websocket, user_id, user_name)
"""

REPOSITORY_CONTENTS = """
# Define your custom repository.
# If you've created a custom table, 
# you'll also need to create a corresponding repository.

# Example
# from arbiter.api.repository import BaseCRUDRepository
# from .model import MyCustomModel

# class MyCustomModelRepository(BaseCRUDRepository[MyCustomModel]):
#     def __init__(self) -> None:
#         super().__init__(MyCustomModel)

"""

MODEL_CONTENTS = """
# Define your custom table.

# Example
# from sqlmodel import Field, Relationship
# from arbiter.api.models import PKModel, BaseSQLModel

# class MyCustomModelBase(BaseSQLModel):
#     someting_number_value: int = Field(default=0)

# class MyCustomModel(MyCustomModelBase, PKModel, table=True):
#     __tablename__ = "my_custom" # Table name used by the DB
"""

CONFIG_CONTENTS = """
[project]
app_env = local
access_token_key = access
refresh_token_key = refresh

[fastapi]
host = 0.0.0.0
port = 9991

[database]
url = postgresql+asyncpg://arbiter:arbiter@localhost:5432/arbiter

[gametester]
developer_token = eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZDEiOiI2MzlhYmY4ODhjM2QyYzJjNjI1YmJiODYiLCJpZDIiOiI2NTM3MWI4MTM1NTdjZDQzODgzNWI0ZmIifQ.TXDzTOvbVHvOO-I2AoUEzL07Me5VrRKPfrc3dlLL85s
playtime_minute = 30
"""

CONTENTS = {
    MAIN_FILE: MAIN_CONTENTS,
    ENGINE_FILE: ENGINE_CONTENTS,
    REPOSITORY_FILE: REPOSITORY_CONTENTS,
    MODEL_FILE: MODEL_CONTENTS,
    CONFIG_FILE: CONFIG_CONTENTS
}

def create_project_structure(project_path='.'):
    """
    Creates a basic project structure with predefined files and directories.

    :param project_path: Base path where the project will be created
    """
    # Define the structure
    project_structure = {
        ".": [MAIN_FILE,
              ENGINE_FILE, 
              REPOSITORY_FILE, 
              MODEL_FILE]  # Files in the root of the project
    }


    # Create the project directory
    os.makedirs(project_path, exist_ok=True)

    # Create subdirectories and files
    for directory, files in project_structure.items():
        dir_path = os.path.join(project_path, directory)
        os.makedirs(dir_path, exist_ok=True)

        for file in files:
            file_path = os.path.join(dir_path, file)
            with open(file_path, 'w') as f:
                f.write(CONTENTS[file].strip() if CONTENTS[file] else "")

    print(f"Project created at {project_path}")

def create_default_config_file(config_file_path):
    """
    Creates a default arbiter.setting.ini file with predefined settings.
    """
    # Create the config file with default content
    with open(os.path.join(config_file_path, CONFIG_FILE), 'w') as file:
        file.write(CONFIG_CONTENTS.strip())  
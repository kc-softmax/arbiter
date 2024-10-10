from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime
from typing import Any

ALLOWED_TYPES = (BaseModel, tuple, list, dict, int, str, float, bool, bytes, datetime, None, Any)

ASYNC_TASK_CLOSE_MESSAGE = b'q__end__q'

PROJECT_NAME  = "arbiter"
CONFIG_FILE = "arbiter.setting.ini"

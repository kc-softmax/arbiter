from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime
from typing import Any

ALLOWED_TYPES = (BaseModel, tuple, list, dict, int, str, float, bool, bytes, datetime, None, Any)

ASYNC_TASK_CLOSE_MESSAGE = b'q__end__q'

PROJECT_NAME  = "arbiter"
CONFIG_FILE = "arbiter.setting.ini"
DEFAULT_CONFIG = {
    'arbiter_password': '',
    'arbiter_send_timeout': 5,
    'warp_in_timeout': 10,
    'system_timeout': 30,
    'service_timeout': 30,
    'service_health_check_interval': 3,
    'service_health_check_func_clock': 0.1,
    'service_retry_count': 3,
    'service_pending_timeout': 30,
}
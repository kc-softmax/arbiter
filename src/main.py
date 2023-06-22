from typing import Union

from fastapi import FastAPI
from auth.service import login_by_device_id, register_user_by_device_id
from src.auth.models import create_db_and_tables

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/register/{device_id}")
def login(device_id: str):
    return register_user_by_device_id(device_id=device_id)


@app.get("/login/{device_id}")
def login(device_id: str):
    return login_by_device_id(device_id=device_id)
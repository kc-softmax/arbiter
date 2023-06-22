from typing import Union
from fastapi import FastAPI
from database import create_db_and_tables
from auth.service import login_by_device_id, register_user_by_device_id
from auth.router import router as auth_router

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


app.include_router(auth_router)

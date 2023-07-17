from fastapi.encoders import jsonable_encoder
from typing import Optional
from dataclasses import Field
from typing import Any, Optional
from fastapi import FastAPI
from sqlmodel import create_engine, func, select
from sqlmodel import SQLModel, Session, Field
from faker import Faker

from fastapi_pagination import add_pagination
from fastapi_pagination.cursor import CursorPage
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi_pagination.ext.sqlalchemy import count_query, exec_pagination


from server.custom_cursor import CustomCursorPage, CustomCursorParams


faker = Faker()

app = FastAPI()
add_pagination(app)

engine = create_engine("sqlite:///abcd.db")


class Hero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str
    age: Optional[int] = None


@app.on_event("startup")
def on_startup():
    with engine.begin() as conn:
        SQLModel.metadata.drop_all(conn)
        SQLModel.metadata.create_all(conn)

    with Session(engine) as session:
        session.add_all([Hero(display_name=str(i)) for i in range(1000)])
        session.commit()


@app.post("/default")
def get_users_default() -> CursorPage[Hero]:
    with Session(engine) as session:
        return paginate(session, select(Hero).order_by(Hero.id))


@app.post("/users")
def get_users(params: CustomCursorParams) -> CustomCursorPage[Hero]:
    with Session(engine) as session:
        return paginate(session, select(Hero).order_by(Hero.id))


@app.post("/pagination_users")
def get_users_test(params: CustomCursorParams) -> CustomCursorPage[Hero]:
    return get_pagination(Hero, params)


def get_pagination(model: any, params: CustomCursorParams):
    with Session(engine) as session:
        page_result = excute_cursor(session, model, params)
        return page_result


def excute_cursor(session, model, params: CustomCursorParams):
    page_result = None
    is_next = False
    cursor = params.cursor if params.cursor else None
    if page_operate_count := params.target_page - params.current_page:
        if page_operate_count > 0:
            is_next = True

    for _ in range(abs(page_operate_count)):
        page_result = exec_pagination(query=select(model).order_by(model.id.desc()),
                                      conn=session,
                                      params=CustomCursorParams(cursor=cursor, size=params.size)
                                      )
        if is_next:
            cursor = page_result.next_page
        else:
            cursor = page_result.previous_page
    page_result.total = session.scalar(select(func.count(model.id)))
    return page_result

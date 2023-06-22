from typing import Any
import click
import typer
from sqlmodel import Session, select
from database import create_db_and_tables, engine
from auth.models import User

app = typer.Typer()


# click custom type 가능하게
_get_click_type = typer.main.get_click_type


def supersede_get_click_type(
    *, annotation: Any, parameter_info: typer.main.ParameterInfo
) -> click.ParamType:
    if hasattr(annotation, "parse_raw"):

        class CustomParamType(click.ParamType):
            def convert(self, value, param, ctx):
                return annotation.parse_raw(value)

        return CustomParamType()
    else:
        return _get_click_type(annotation=annotation, parameter_info=parameter_info)

typer.main.get_click_type = supersede_get_click_type

@app.command()
def register_user_by_device_id(device_id: str) -> User:
    with Session(engine) as session:
        user = User(device_id=device_id)
        session.add(user)
        session.commit()
        #table 값을 객체에 부여해준다.
        session.refresh(user)
        print(user)
        return user

@app.command()
def login_by_device_id(device_id: str) -> User:
    with Session(engine) as session:
        # first or None
        statement = select(User).where(User.device_id == device_id)
        results = session.exec(statement)
        user = results.first()
        print(user)
        return user

@app.command()
def resister_user_by_email(email: str, password: str) -> User:
    with Session(engine) as session:
        user = User(email=email, password=password)
        session.add(user)
        session.commit()
        #table 값을 객체에 부여해준다.
        session.refresh(user)
        print(user)
        return user

@app.command()
def login_by_email(email: str, password: str) -> User | None:
    with Session(engine) as session:
        # first or None
        statement = select(User).where(User.email == email).where(User.password == password)
        results = session.exec(statement)
        user = results.first()
        print(user)
        return user

@app.command()
def check_user_by_email(email: str) -> User | None:
    with Session(engine) as session:
        # first or None
        statement = select(User).where(User.email == email)
        results = session.exec(statement)
        user = results.first()
        print(user)
        return user


@app.command()
def delete_user(user_id: int) -> bool:
    is_success = False
    with Session(engine) as session:
        statement = select(User).where(User.id == user_id)
        results = session.exec(statement)
        try:
            # no row exception 처리
            user = results.one()
            session.delete(user)
            session.commit()
            is_success = True
        except Exception as e:
            print(e)
        return is_success

@app.command()
def get_user(user_id: int) -> User | None:
    with Session(engine) as session:
        user = session.get(User, user_id)
        print(user)
        return user

@app.command()
def update_user(user_id: int, user: User) -> User | None:
    with Session(engine) as session:
        db_user = session.get(User, user_id)
        if not db_user:
            return None
        hero_data = user.dict(exclude_unset=True)
        for key, value in hero_data.items():
            setattr(db_user, key, value)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user


if __name__ == "__main__":
    create_db_and_tables()
    app()

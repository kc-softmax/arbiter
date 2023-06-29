from typing import Annotated, Any
import click
import typer
from sqlmodel import Session, select
from database import create_db_and_tables, engine
from auth.models import User

app = typer.Typer()


@app.command('register_user_by_device_id')
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

@app.command('resister_user_by_email')
def resister_user_by_email(email: str, password: str) -> User:
    with Session(engine) as session:
        user = User(email=email, password=password)
        session.add(user)
        session.commit()
        #table 값을 객체에 부여해준다.
        session.refresh(user)
        print(user)
        return user

@app.command('login_by_email')
def login_by_email(email: str, password: str) -> User | None:
    with Session(engine) as session:
        # first or None
        statement = select(User).where(User.email == email).where(User.password == password)
        results = session.exec(statement)
        user = results.first()
        print(user)
        return user

@app.command('check_user_by_email')
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

@app.command('get_user')
def get_user(user_id: int) -> User | None:
    with Session(engine) as session:
        user = session.get(User, user_id)
        print(user)
        return user

def parse_custom_class(value: str):
    return User.parse_raw(value)

@app.command('update_user')
def update_user(
    user_id: int,
    user: User = typer.Argument(parser=parse_custom_class)
) -> User | None:
    with Session(engine) as session:
        db_user = session.get(User, user_id)
        if not db_user:
            return None
        user_data = user.dict(exclude_unset=True)
        for key, value in user_data.items():
            setattr(db_user, key, value)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user


if __name__ == "__main__":
    create_db_and_tables()
    app()

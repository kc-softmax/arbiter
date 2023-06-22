import typer
from sqlmodel import Session, select
from database import create_db_and_tables, engine
from auth.models import User

app = typer.Typer()

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
def create_auth_token(user_id: int):
    return "this is auth token"

@app.command()
def refresh_auth_token(auth_token: str):
    return "this is refresh token"

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
def get_user(user_id: int):
    return "this is get user"

if __name__ == "__main__":
    create_db_and_tables()
    app()

from sqlmodel import Session, select

from database import engine
from auth.models import User, LoginType


def register_user_by_device_id(device_id: str) -> User:
    with Session(engine) as session:
        user = User(device_id=device_id, login_type=LoginType.GUEST)
        session.add(user)
        session.commit()
        # table 값을 객체에 부여해준다.
        session.refresh(user)
    return user


def login_by_device_id(device_id: str) -> User:
    with Session(engine) as session:
        # first or None
        statement = select(User).where(User.device_id == device_id)
        results = session.exec(statement)
        user = results.first()
    return user


def resister_user_by_email(email: str, password: str) -> User:
    with Session(engine) as session:
        user = User(email=email, password=password, login_type=LoginType.EMAIL)
        session.add(user)
        session.commit()
        # table 값을 객체에 부여해준다.
        session.refresh(user)
    return user


def login_by_email(email: str, password: str) -> User | None:
    with Session(engine) as session:
        # first or None
        statement = select(User).where(
            User.email == email).where(User.password == password)
        results = session.exec(statement)
        user = results.first()
    return user


def check_user_by_email(email: str) -> User | None:
    with Session(engine) as session:
        # first or None
        statement = select(User).where(User.email == email)
        results = session.exec(statement)
        user = results.first()
    return user


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


def get_user(user_id: int) -> User | None:
    with Session(engine) as session:
        user = session.get(User, user_id)
    return user


def update_user(
    user_id: int,
    user: User
) -> User | None:
    with Session(engine) as session:
        db_user = session.get(User, user_id)
        if db_user:
            user_data = user.dict(exclude_unset=True)
            for key, value in user_data.items():
                setattr(db_user, key, value)
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
    return db_user

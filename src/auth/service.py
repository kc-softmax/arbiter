from sqlmodel import Session, select

from database import engine
from auth.models import User, LoginType, ConsoleUser, Role


class UserService:
    def register_user_by_device_id(self, device_id: str) -> User:
        with Session(engine) as session:
            user = User(device_id=device_id, login_type=LoginType.GUEST)
            session.add(user)
            session.commit()
            # table 값을 객체에 부여해준다.
            session.refresh(user)
        return user

    def login_by_device_id(self, device_id: str) -> User:
        with Session(engine) as session:
            # first or None
            statement = select(User).where(User.device_id == device_id)
            results = session.exec(statement)
            user = results.first()
        return user

    def resister_user_by_email(
            self,
            email: str,
            password: str
    ) -> User:
        with Session(engine) as session:
            user = User(email=email, password=password, login_type=LoginType.EMAIL)
            session.add(user)
            session.commit()
            # table 값을 객체에 부여해준다.
            session.refresh(user)
        return user

    def login_by_email(self, email: str, password: str) -> User | None:
        with Session(engine) as session:
            # first or None
            statement = select(User).where(User.email == email).where(User.password == password)
            results = session.exec(statement)
            user = results.first()
        return user

    def check_user_by_email(self, email: str) -> User | None:
        with Session(engine) as session:
            # first or None
            statement = select(User).where(User.email == email)
            results = session.exec(statement)
            user = results.first()
        return user

    def delete_user(self, user_id: int) -> bool:
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

    def get_user(self, user_id: int) -> User | None:
        with Session(engine) as session:
            user = session.get(User, user_id)
        return user

    def update_user(
        self,
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


class ConsoleUserService:
    def register_console_user(
            self,
            email: str,
            password: str,
            user_name: str,
            role: Role
    ) -> ConsoleUser:
        with Session(engine) as session:
            console_user = ConsoleUser(
                email=email,
                password=password,
                user_name=user_name,
                role=role
            )
            session.add(console_user)
            session.commit()
            session.refresh(console_user)
        return console_user

    def update_console_user(
        self,
        console_user_id: int,
        console_user: ConsoleUser
    ) -> ConsoleUser:
        with Session(engine) as session:
            db_console_user = session.get(ConsoleUser, console_user_id)
            if db_console_user:
                user_data = console_user.dict(exclude_unset=True)
                for key, value in user_data.items():
                    setattr(db_console_user, key, value)
                session.add(db_console_user)
                session.commit()
                session.refresh(db_console_user)
        return db_console_user

    def get_console_user_all(self) -> list[ConsoleUser]:
        with Session(engine) as session:
            statement = select(ConsoleUser)
            console_users = session.exec(statement).all()
            return console_users

    def get_console_by_role(self, role: Role) -> list[ConsoleUser]:
        with Session(engine) as session:
            statement = select(ConsoleUser).where(ConsoleUser.role == role)
            console_users = session.exec(statement).all()
            return console_users

    def get_console_user_by_id(self, console_user_id: int) -> ConsoleUser | None:
        with Session(engine) as session:
            statement = select(ConsoleUser).where(ConsoleUser.id == console_user_id)
            console_users = session.exec(statement).first()
            return console_users

    def delete_console_user(self, console_user_id: int) -> bool:
        is_success = False
        with Session(engine) as session:
            statement = select(ConsoleUser).where(ConsoleUser.id == console_user_id)
            results = session.exec(statement)
            try:
                # no row exception 처리
                console_user = results.one()
                session.delete(console_user)
                session.commit()
                is_success = True
            except Exception as e:
                print(e)
        return is_success

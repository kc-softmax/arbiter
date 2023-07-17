from typing import Any
from fastapi import Request
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi_pagination.ext.sqlmodel import paginate


from server.auth.models import User, LoginType, ConsoleUser, Role
from server.custom_cursor import CustomCursorPage, CustomCursorParams


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user_by_device_id(self, device_id: str, display_name: str = '') -> User:
        user = User(device_id=device_id, login_type=LoginType.GUEST, display_name=display_name)
        self.session.add(user)
        await self.session.commit()
        # table 값을 객체에 부여해준다.
        await self.session.refresh(user)
        return user

    async def login_by_device_id(self, device_id: str) -> User:
        # first or None
        statement = select(User).where(User.device_id == device_id)
        results = await self.session.exec(statement)
        user = results.first()
        return user

    async def register_user_by_email(
            self,
            email: str,
            password: str,
            display_name: str = ''
    ) -> User:
        user = User(email=email, password=password, login_type=LoginType.EMAIL, display_name=display_name)
        self.session.add(user)
        await self.session.commit()
        # table 값을 객체에 부여해준다.
        await self.session.refresh(user)
        return user

    async def login_by_email(self, email: str, password: str) -> User | None:
        # first or None
        statement = select(User).where(User.email == email).where(User.password == password)
        results = await self.session.exec(statement)
        user = results.first()
        return user

    async def check_user_by_email(self, email: str) -> User | None:
        # first or None
        statement = select(User).where(User.email == email)
        results = await self.session.exec(statement)
        user = results.first()
        return user

    async def check_user_by_device_id(self, device_id: str) -> User | None:
        # first or None
        statement = select(User).where(User.device_id == device_id)
        results = await self.session.exec(statement)
        user = results.first()
        return user

    async def delete_user(self, user_id: int) -> bool:
        is_success = False
        statement = select(User).where(User.id == user_id)
        results = await self.session.exec(statement)
        try:
            # no row exception 처리
            user = results.one()
            await self.session.delete(user)
            await self.session.commit()
            is_success = True
        except Exception as e:
            print(e)
        return is_success

    async def get_user(self, user_id: int) -> User | None:
        user = await self.session.get(User, user_id)
        return user

    async def update_user(
        self,
        user_id: int,
        user: User
    ) -> User | None:
        db_user = await self.session.get(User, user_id)
        if db_user:
            user_data = user.dict(exclude_unset=True)
            for key, value in user_data.items():
                setattr(db_user, key, value)
            self.session.add(db_user)
            await self.session.commit()
            await self.session.refresh(db_user)
        return db_user


class ConsoleUserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_console_user(
            self,
            email: str,
            password: str,
            role: Role,
            user_name: str = ''
    ) -> ConsoleUser:
        console_user = ConsoleUser(
            email=email,
            password=password,
            user_name=user_name,
            role=role
        )
        self.session.add(console_user)
        await self.session.commit()
        await self.session.refresh(console_user)
        return console_user

    async def login_by_email(self, email: str, password: str) -> User | None:
        statement = (
            select(ConsoleUser)
            .where(ConsoleUser.email == email)
            .where(ConsoleUser.password == password)
        )
        results = await self.session.exec(statement)
        console_user = results.first()
        return console_user

    async def update_console_user(
        self,
        console_user_id: int,
        console_user: ConsoleUser
    ) -> ConsoleUser:
        db_console_user = await self.session.get(ConsoleUser, console_user_id)
        if db_console_user:
            user_data = console_user.dict(exclude_unset=True)
            for key, value in user_data.items():
                setattr(db_console_user, key, value)
            self.session.add(db_console_user)
            await self.session.commit()
            await self.session.refresh(db_console_user)
        return db_console_user

    async def get_console_user_all(self) -> list[ConsoleUser]:
        statement = select(ConsoleUser)
        results = await self.session.exec(statement)
        console_users = results.all()
        return console_users

    async def get_console_by_role(self, role: Role) -> list[ConsoleUser]:
        statement = select(ConsoleUser).where(ConsoleUser.role == role)
        result = await self.session.exec(statement)
        console_users = result.all()
        return console_users

    async def get_console_user_by_id(self, console_user_id: int) -> ConsoleUser | None:
        statement = select(ConsoleUser).where(ConsoleUser.id == console_user_id)
        results = await self.session.exec(statement)
        console_user = results.first()
        return console_user

    async def delete_console_user(self, console_user_id: int) -> bool:
        is_success = False
        statement = select(ConsoleUser).where(ConsoleUser.id == console_user_id)
        results = await self.session.exec(statement)
        try:
            # no row exception 처리
            console_user = results.one()
            await self.session.delete(console_user)
            await self.session.commit()
            is_success = True
        except Exception as e:
            print(e)
        return is_success


class PaginationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pagination(self, request: Request, model: Any) -> CustomCursorPage[Any]:
        params = CustomCursorParams(**request.query_params)
        result = None
        for _ in range(self.get_page_step(request)):
            result = await paginate(self.session, select(model).order_by(model.id), params=params)
            params.cursor = result.next_page if result.next_page else result.previous_page
        result.total = await self.session.scalar(select(func.count(model.id)))
        return result

    def get_page_step(self, request) -> int:
        request_args = dict(request.query_params)
        page_step = int(request_args['target_page']) - int(request_args['current_page'])
        return abs(page_step)

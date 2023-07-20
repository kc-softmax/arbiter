from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.auth.models import User, LoginType, ConsoleUser, Role


class BaseService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    # TODO: 서비스 CRUD 함수 통일하기


class UserService(BaseService):
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

    # TODO: 삭제
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

    async def delete_users(self, ids: list[int]):
        try:
            for id in ids:
                statement = select(User).where(User.id == id)
                result = await self.session.exec(statement)
                user = result.one()
                await self.session.delete(user)
        except Exception as e:
            print(e)
            await self.session.rollback()
            return False
        await self.session.commit()
        return True

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


class ConsoleUserService(BaseService):
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

    # TODO: 삭제
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

    async def delete_console_users(self, ids: list[int]) -> bool:
        try:
            for id in ids:
                statement = select(ConsoleUser).where(ConsoleUser.id == id)
                result = await self.session.exec(statement)
                console_user = result.one()
                await self.session.delete(console_user)
        except Exception as e:
            print(e)
            await self.session.rollback()
            return False
        await self.session.commit()
        return True

    # 마지막 owner 인지 확인
    async def check_last_console_owner_for_update(self, console_user_id: int) -> bool:
        consol_users = await self.get_console_by_role(Role.OWNER)
        if len(consol_users) == 1:
            if console_user_id == consol_users[0].id:
                return True
        return False

    # delete 용, 멀티 삭제 요청 시 적어도 한개는 남게
    async def check_last_console_owner_for_delete(self, ids: list[int]) -> bool:
        console_user_count = await self.session.scalar(
            select(func.count(ConsoleUser.id)).where(ConsoleUser.role == Role.OWNER)
        )
        req_console_user_count = await self.session.scalar(
            select(func.count(ConsoleUser.id)).where(ConsoleUser.id.in_(ids)).where(ConsoleUser.role == Role.OWNER)
        )

        # 1개 이하로 남으면 삭제 불가
        if console_user_count - req_console_user_count < 1:
            return True
        return False

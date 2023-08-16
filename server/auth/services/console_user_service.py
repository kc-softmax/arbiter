from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.auth.models import ConsoleUser, Role
from server.database import DatabaseManager


# db 접근은 DatabaseManager로 한다.
db_manager = DatabaseManager[ConsoleUser](ConsoleUser)


async def register_console_user(
    session: AsyncSession,
    email: str,
    password: str,
    role: Role,
    user_name: str = ''
) -> ConsoleUser:
    return await db_manager.create(
        session=session,
        obj=ConsoleUser(
            email=email,
            password=password,
            role=role,
            user_name=user_name
        )
    )


async def login_by_email(
    session: AsyncSession,
    email: str,
    password: str
) -> ConsoleUser | None:
    return await db_manager.get_one(
        session=session,
        obj_clauses=ConsoleUser(
            email=email,
            password=password
        )
    )


async def update_console_user(
    session: AsyncSession,
    console_user_id: int,
    console_user_in: ConsoleUser
) -> ConsoleUser | None:
    console_user = await db_manager.get_one(
        session=session,
        obj_clauses=ConsoleUser(
            id=console_user_id
        )
    )
    if not console_user:
        return None

    return await db_manager.update(
        session=session,
        obj_in=console_user_in,
        obj=console_user
    )


async def get_console_by_role(
    session: AsyncSession,
    role: Role
) -> list[ConsoleUser]:
    return await db_manager.get_all(
        session=session,
        obj_clauses=ConsoleUser(
            role=role
        )
    )


# 정리?
async def get_console_user_by_id(
    session: AsyncSession,
    console_user_id: int
) -> ConsoleUser | None:
    return await db_manager.get_one(
        session=session,
        obj_clauses=ConsoleUser(
            id=console_user_id
        )
    )


async def delete_console_user(session: AsyncSession, console_user_id: int) -> bool | None:
    console_user = await db_manager.get_one(
        session=session,
        obj_clauses=ConsoleUser(
            id=console_user_id
        )
    )
    if not console_user:
        return None
    return await db_manager.delete_one(
        session=session,
        obj=console_user
    )


async def delete_console_users(session: AsyncSession, console_user_ids: list[int]) -> bool:
    return await db_manager.delete_all(
        session=session,
        obj_ids=console_user_ids
    )


async def check_last_console_owner_for_update(
    session: AsyncSession,
    console_user_id: int
) -> bool:
    consol_users = await get_console_by_role(session, Role.OWNER)
    if len(consol_users) == 1:
        if console_user_id == consol_users[0].id:
            return True
    return False


# delete 용, 멀티 삭제 요청 시 적어도 한개는 남게
async def check_last_console_owner_for_delete(
    session: AsyncSession,
    console_user_ids: list[int]
) -> bool:
    console_user_count = await session.scalar(
        select(func.count(ConsoleUser.id))
        .where(ConsoleUser.role == Role.OWNER)
    )
    request_console_user_count = await session.scalar(
        select(func.count(ConsoleUser.id))
        .where(ConsoleUser.id.in_(console_user_ids))
        .where(ConsoleUser.role == Role.OWNER)
    )
    # 1개 이하로 남으면 삭제 불가
    if console_user_count - request_console_user_count < 1:
        return True
    return False

from sqlmodel.ext.asyncio.session import AsyncSession

from server.auth.models import User
from database import DatabaseManager


# db 접근은 DatabaseManager로 한다.
db_manager = DatabaseManager[User](User)


async def register_user_by_device_id(
    session: AsyncSession,
    device_id: str,
    display_name: str = ''
) -> User:
    return await db_manager.create(
        session=session,
        obj=User(
            device_id=device_id,
            display_name=display_name
        )
    )


async def login_by_device_id(session: AsyncSession, device_id: str) -> User:
    return await db_manager.get_one(
        session=session,
        obj_clauses=User(
            device_id=device_id
        )
    )


async def register_user_by_email(
    session: AsyncSession,
    email: str,
    password: str,
    display_name: str = ''
) -> User:
    return await db_manager.create(
        session=session,
        obj=User(
            email=email,
            password=password,
            display_name=display_name
        )
    )


async def login_by_email(
    session: AsyncSession,
    email: str,
    password: str
) -> User | None:
    return await db_manager.get_one(
        session=session,
        obj_clauses=User(
            email=email,
            password=password
        )
    )


async def check_user_by_email(
    session: AsyncSession,
    email: str
) -> User | None:
    return await db_manager.get_one(
        session=session,
        obj_clauses=User(
            email=email
        )
    )


# login_by_device_id 동일
async def check_user_by_device_id(session: AsyncSession, device_id: str) -> User | None:
    return await db_manager.get_one(
        session=session,
        obj_clauses=User(
            device_id=device_id
        )
    )


async def update_user(
    session: AsyncSession,
    user_id: User,
    user_in: User
) -> User | None:
    user = await db_manager.get_one(
        session=session,
        obj_clauses=User(
            id=user_id
        )
    )
    if not user:
        return None

    return await db_manager.update(
        session=session,
        obj_in=user_in,
        obj=user
    )


async def delete_user(session: AsyncSession, user_id: int) -> bool | None:
    user = await db_manager.get_one(
        session=session,
        obj_clauses=User(
            id=user_id
        )
    )
    if not user:
        return None
    return await db_manager.delete_one(
        session=session,
        obj=user
    )


async def delete_users(session: AsyncSession, user_ids: list[int]) -> bool:
    return await db_manager.delete_all(
        session=session,
        obj_ids=user_ids
    )

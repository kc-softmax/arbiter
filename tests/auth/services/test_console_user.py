import pytest
import pytest_asyncio
from uuid import uuid4
from sqlmodel.ext.asyncio.session import AsyncSession

from server.auth.models import ConsoleUser, Role
from server.auth.services import console_user_service


# test data fixture
@pytest_asyncio.fixture(scope='function')
async def case_register_by_email(async_session: AsyncSession) -> ConsoleUser:
    return await console_user_service.register_console_user(
        session=async_session,
        email='test_email@email.com',
        password='test_password', role=Role.OWNER
    )


# function test
@pytest.mark.asyncio
async def test_register_console_user(async_session: AsyncSession):
    expected = ConsoleUser(email='test_email', password='test_password', role=Role.OWNER)
    get_data = await console_user_service.register_console_user(
        session=async_session,
        email=expected.email,
        password=expected.password,
        role=expected.role
    )
    assert expected.email == get_data.email


@pytest.mark.asyncio
async def test_login_by_email(async_session: AsyncSession, case_register_by_email: ConsoleUser):
    expected_email = case_register_by_email.email
    get_data = await console_user_service.login_by_email(
        session=async_session,
        email=case_register_by_email.email,
        password=case_register_by_email.password
    )
    assert expected_email == get_data.email


@pytest.mark.asyncio
async def test_get_console_user_by_id(async_session: AsyncSession, case_register_by_email: ConsoleUser):
    get_data = await console_user_service.get_console_user_by_id(
        session=async_session,
        console_user_id=case_register_by_email.id
    )
    assert get_data.id == case_register_by_email.id


@pytest.mark.asyncio
async def test_update_console_user(
    async_session: AsyncSession,
    case_register_by_email: ConsoleUser,
):
    update_data = {
        'user_name': 'test_user_name',
        'role': Role.MAINTAINER
    }
    expected = case_register_by_email.dict()
    for key, value in update_data.items():
        expected[key] = value

    updated_console_user = await console_user_service.update_console_user(
        async_session,
        case_register_by_email.id,
        ConsoleUser(**update_data)
    )
    assert expected == updated_console_user.dict()


@pytest.mark.asyncio
async def test_delete_user(async_session: AsyncSession, case_register_by_email: ConsoleUser):
    expected_none_user = await console_user_service.delete_console_user(async_session, 1000)
    assert expected_none_user == None

    is_delete_success = await console_user_service.delete_console_user(async_session, case_register_by_email.id)
    assert True == is_delete_success


@pytest.mark.asyncio
async def test_delete_console_users(async_session: AsyncSession):
    # 테스트용 유저 생성
    owner_users = [
        await console_user_service.register_console_user(
            session=async_session,
            email=uuid4(),
            password=uuid4(),
            role=Role.MAINTAINER
        ) for _ in range(10)
    ]
    # 성공 테스트를 위해 owner 유저 추가
    pass_user_ids = [user.id for user in owner_users]
    # 실패 테스트를 위해 존재하지 않는 유저 id 추가
    fail_user_ids = pass_user_ids + [1000]

    is_delete_success = await console_user_service.delete_console_users(async_session, fail_user_ids)
    assert False == is_delete_success

    is_delete_success = await console_user_service.delete_console_users(async_session, pass_user_ids)
    assert True == is_delete_success


@pytest.mark.asyncio
async def test_check_last_console_owner_for_update(
    async_session: AsyncSession,
    case_register_by_email: ConsoleUser
):
    base_data = await console_user_service.login_by_email(
        async_session,
        case_register_by_email.email,
        case_register_by_email.password
    )
    is_last = await console_user_service.check_last_console_owner_for_update(async_session, base_data.id)
    assert True == is_last


@pytest.mark.asyncio
async def test_check_last_console_owner_for_delete(async_session: AsyncSession):
    # 테스트용 owner 유저 생성
    first_console_user = await console_user_service.register_console_user(
        session=async_session,
        email=uuid4(),
        password=uuid4(),
        role=Role.OWNER
    )

    # 테스트용 유저 생성
    owner_users = [
        await console_user_service.register_console_user(
            session=async_session,
            email=uuid4(),
            password=uuid4(),
            role=Role.OWNER
        ) for _ in range(10)
    ]
    # 성공 테스트를 위해 생성한 유저 id 추가
    pass_user_ids = [user.id for user in owner_users]
    # 실패 테스트를 위해 먼저 생성된 owner id 추가
    fail_user_ids = pass_user_ids + [first_console_user.id]

    is_last = await console_user_service.check_last_console_owner_for_delete(
        session=async_session,
        console_user_ids=pass_user_ids
    )
    assert False == is_last

    is_last = await console_user_service.check_last_console_owner_for_delete(
        session=async_session,
        console_user_ids=fail_user_ids
    )
    assert True == is_last

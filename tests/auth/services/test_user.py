import pytest
import pytest_asyncio
from uuid import uuid4
from sqlmodel.ext.asyncio.session import AsyncSession


from server.auth.models import User
from auth.services import user_service


# test data fixture
@pytest_asyncio.fixture(scope='function')
async def case_register_by_device_id(async_session: AsyncSession) -> User:
    return await user_service.register_user_by_device_id(async_session, 'test_device_id')


@pytest_asyncio.fixture(scope='function')
async def case_register_by_email(async_session) -> User:
    return await user_service.register_user_by_email(
        session=async_session,
        email='user@email.com',
        password='test_password'
    )


# function test
@pytest.mark.asyncio
async def test_register_user_by_device_id(async_session: AsyncSession):
    # 먼저 register 테스트 진행
    expected_device_id = 'test_device_id'
    register_data = await user_service.register_user_by_device_id(async_session, expected_device_id)
    assert expected_device_id == register_data.device_id


@pytest.mark.asyncio
async def test_login_by_device_id(async_session, case_register_by_device_id: User):
    login_data = await user_service.login_by_device_id(
        session=async_session,
        device_id=case_register_by_device_id.device_id
    )
    assert login_data.device_id == case_register_by_device_id.device_id


@pytest.mark.asyncio
async def test_register_user_by_email(async_session: AsyncSession):
    expected = User(email='test_email', password='test_password')
    register_data = await user_service.register_user_by_email(
        session=async_session,
        email=expected.email,
        password=expected.password
    )
    assert register_data.email == expected.email


@pytest.mark.asyncio
async def test_login_by_email(async_session: AsyncSession, case_register_by_email: User):
    expected_email = case_register_by_email.email
    login_data = await user_service.login_by_email(
        session=async_session,
        email=case_register_by_email.email,
        password=case_register_by_email.password
    )
    assert expected_email == login_data.email


@pytest.mark.asyncio
async def test_check_user_by_email(async_session: AsyncSession, case_register_by_email: User):
    expected_email = case_register_by_email.email
    get_data = await user_service.check_user_by_email(
        session=async_session,
        email=case_register_by_email.email
    )
    assert expected_email == get_data.email


@pytest.mark.asyncio
async def test_check_user_by_device_id(async_session: AsyncSession, case_register_by_device_id: User):
    expected_device_id = case_register_by_device_id.device_id
    get_data = await user_service.check_user_by_device_id(
        session=async_session,
        device_id=case_register_by_device_id.device_id
    )
    assert expected_device_id == get_data.device_id


@pytest.mark.asyncio
async def test_user_update(async_session: AsyncSession, case_register_by_email: User):
    update_data = {
        'display_name': 'test_display_name',
        'access_token': 'test_access_token',
        'refresh_token': 'test_refresh_token'
    }
    expected = case_register_by_email.dict()
    for key, value in update_data.items():
        expected[key] = value

    updated_user = await user_service.update_user(
        session=async_session,
        user_id=case_register_by_email.id,
        user_in=User(**update_data),
    )
    assert expected == updated_user.dict()


@pytest.mark.asyncio
async def test_delete_user(async_session: AsyncSession, case_register_by_email: User):
    expected_none_user = await user_service.delete_user(async_session, 1000)
    assert expected_none_user == None

    is_delete_success = await user_service.delete_user(async_session, case_register_by_email.id)
    assert True == is_delete_success


@pytest.mark.asyncio
async def test_delete_users(async_session: AsyncSession):
    # 테스트용 유저 생성
    users = [await user_service.register_user_by_device_id(async_session, uuid4()) for _ in range(10)]
    pass_user_ids = [user.id for user in users]
    # 실패 테스트를 위해 존재하지 않는 유저 id 추가
    fail_user_ids = pass_user_ids + [1000]

    is_delete_success = await user_service.delete_users(
        session=async_session,
        user_ids=fail_user_ids
    )
    assert False == is_delete_success

    is_delete_success = await user_service.delete_users(
        async_session,
        pass_user_ids
    )
    assert True == is_delete_success

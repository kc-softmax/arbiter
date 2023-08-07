import random
import pytest
from uuid import uuid4

import pytest_asyncio

from server.auth.models import ConsoleUser, User, Role
from server.auth.service import ConsoleUserService, UserService


class TestUserService:
    @pytest.fixture(scope='function')
    def test_service(self, async_session) -> UserService:
        return UserService(session=async_session)

    # 중복으로 생성
    @pytest_asyncio.fixture(scope='function')
    async def case_register_by_device_id(self, test_service: UserService) -> User:
        return await test_service.register_user_by_device_id('test_device_id')

    @pytest_asyncio.fixture(scope='function')
    async def case_register_by_email(self, test_service: UserService) -> User:
        return await test_service.register_user_by_email(
            email='test_email@email.com', password='test_password'
        )

    @pytest.fixture(scope='function')
    def test_data_for_login_device_id(self):
        return User(device_id='test_device_id')

    @pytest.mark.asyncio
    async def test_register_user_by_device_id(self, test_service: UserService):
        # 먼저 register 테스트 진행
        expected = User(device_id='test_device_id')
        register_data = await test_service.register_user_by_device_id(expected.device_id)
        assert register_data.device_id == expected.device_id

    @pytest.mark.asyncio
    async def test_login_by_device_id(self, test_service: UserService, case_register_by_device_id: User):
        login_data = await test_service.login_by_device_id(case_register_by_device_id.device_id)
        assert login_data.device_id == case_register_by_device_id.device_id

    @pytest.mark.asyncio
    async def test_register_user_by_email(self, test_service: UserService):
        expected = User(email='test_email', password='test_password')

        register_data = await test_service.register_user_by_email(
            email=expected.email,
            password=expected.password
        )
        assert register_data.email == expected.email

    @pytest.mark.asyncio
    async def test_login_by_email(self, test_service: UserService, case_register_by_email: User):
        login_data = await test_service.login_by_email(
            case_register_by_email.email,
            case_register_by_email.password
        )
        assert login_data.email == case_register_by_email.email

    @pytest.mark.asyncio
    async def test_check_user_by_email(self, test_service: UserService, case_register_by_email: User):
        get_data = await test_service.check_user_by_email(case_register_by_email.email)
        assert get_data.email == case_register_by_email.email

    @pytest.mark.asyncio
    async def test_check_user_by_device_id(self, test_service: UserService, case_register_by_device_id: User):
        get_data = await test_service.check_user_by_device_id(case_register_by_device_id.device_id)
        assert get_data.device_id == case_register_by_device_id.device_id

    @pytest.mark.asyncio
    async def test_user_update(self, test_service: UserService, case_register_by_email: User):
        update_data = {
            'display_name': 'test_display_name',
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token'
        }

        dict_case_register_by_email = case_register_by_email.dict()
        for key, value in update_data.items():
            dict_case_register_by_email[key] = value

        updated_user = await test_service.update_user(
            case_register_by_email.id,
            User(**update_data)
        )

        assert dict_case_register_by_email == updated_user.dict()

    @pytest.mark.asyncio
    async def test_delete_users(self, test_service: UserService):
        # 테스트용 유저 생성
        users = [await test_service.register_user_by_device_id(uuid4()) for _ in range(10)]
        pass_user_ids = [user.id for user in users]
        # 실패 테스트를 위해 존재하지 않는 유저 id 추가
        fail_user_ids = pass_user_ids + [1000]

        is_delete_success = await test_service.delete_users(fail_user_ids)
        assert is_delete_success == False

        is_delete_success = await test_service.delete_users(pass_user_ids)
        assert is_delete_success == True


class TestConsoleUserService:
    @pytest.fixture(scope='function')
    def test_service(self, async_session) -> ConsoleUserService:
        return ConsoleUserService(session=async_session)

    @pytest_asyncio.fixture(scope='function')
    async def case_register_by_email(self, test_service: ConsoleUserService) -> ConsoleUser:
        return await test_service.register_console_user(
            email='test_email@email.com', password='test_password', role=Role.OWNER
        )

    @pytest.mark.asyncio
    async def test_register_console_user(self, test_service: ConsoleUserService):
        expected = ConsoleUser(email='test_email', password='test_password', role=Role.OWNER)

        get_data = await test_service.register_console_user(
            email=expected.email,
            password=expected.password,
            role=expected.role
        )
        assert get_data.email == expected.email

    @pytest.mark.asyncio
    async def test_login_by_email(self, test_service: ConsoleUserService, case_register_by_email: ConsoleUser):
        get_data = await test_service.login_by_email(
            case_register_by_email.email,
            case_register_by_email.password
        )
        assert get_data.email == case_register_by_email.email

    @pytest.mark.asyncio
    async def test_get_console_user_by_id(self, test_service: ConsoleUserService, case_register_by_email: ConsoleUser):
        get_data = await test_service.get_console_user_by_id(case_register_by_email.id)
        assert get_data.id == case_register_by_email.id

    @pytest.mark.asyncio
    async def test_update_console_user(
        self, test_service: ConsoleUserService, case_register_by_email: ConsoleUser,
    ):
        update_data = {
            'user_name': 'test_user_name',
            'role': Role.MAINTAINER
        }

        dict_case_register_by_email = case_register_by_email.dict()
        for key, value in update_data.items():
            dict_case_register_by_email[key] = value

        updated_console_user = await test_service.update_console_user(
            case_register_by_email.id,
            ConsoleUser(**update_data)
        )

        assert dict_case_register_by_email == updated_console_user.dict()

    @pytest.mark.asyncio
    async def test_delete_console_users(self, test_service: ConsoleUserService):
        # 테스트용 유저 생성
        owner_users = [
            await test_service.register_console_user(
                email=uuid4(), password=uuid4(), role=Role.MAINTAINER
            ) for _ in range(10)
        ]
        # 성공 테스트를 위해 owner 유저 추가
        pass_user_ids = [user.id for user in owner_users]
        # 실패 테스트를 위해 존재하지 않는 유저 id 추가
        fail_user_ids = pass_user_ids + [1000]

        is_delete_success = await test_service.delete_console_users(fail_user_ids)
        assert is_delete_success == False

        is_delete_success = await test_service.delete_console_users(pass_user_ids)
        assert is_delete_success == True

    @pytest.mark.asyncio
    async def test_check_last_console_owner_for_update(
        self,
        test_service: ConsoleUserService,
        case_register_by_email: ConsoleUser
    ):
        base_data = await test_service.login_by_email(
            case_register_by_email.email,
            case_register_by_email.password
        )
        is_last = await test_service.check_last_console_owner_for_update(base_data.id)
        assert is_last == True

    @pytest.mark.asyncio
    async def test_check_last_console_owner_for_delete(self, test_service: ConsoleUserService):
        # 테스트용 owner 유저 생성
        first_console_user = await test_service.register_console_user(
            email=uuid4(), password=uuid4(), role=Role.OWNER
        )

        # 테스트용 유저 생성
        owner_users = [
            await test_service.register_console_user(
                email=uuid4(), password=uuid4(), role=Role.OWNER
            ) for _ in range(10)
        ]
        # 성공 테스트를 위해 생성한 유저 id 추가
        pass_user_ids = [user.id for user in owner_users]
        # 실패 테스트를 위해 먼저 생성된 owner id 추가
        fail_user_ids = pass_user_ids + [first_console_user.id]

        is_last = await test_service.check_last_console_owner_for_delete(pass_user_ids)
        assert is_last == False

        is_last = await test_service.check_last_console_owner_for_delete(fail_user_ids)
        assert is_last == True

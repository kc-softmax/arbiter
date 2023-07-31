import pytest
from uuid import uuid4

from server.auth.models import ConsoleUser, User, Role
from server.auth.service import ConsoleUserService, UserService


class TestUserService:
    @pytest.fixture(scope='class')
    def test_service(self, async_session) -> UserService:
        return UserService(session=async_session)

    @pytest.fixture(scope='class')
    def test_data(self):
        return User(email='test_email@email.com', password='test_password', display_name='test_name', device_id='test_device_id')

    @pytest.fixture(scope='class')
    def expect_data(self):
        return User(email='test_email@email.com', password='test_password', display_name='update_name', device_id='test_device_id')

    @pytest.mark.asyncio
    async def test_register_user_by_device_id(self, test_service: UserService, test_data: User, expect_data: User):
        get_data = await test_service.register_user_by_device_id(test_data.device_id)
        assert get_data.device_id == expect_data.device_id

    @pytest.mark.asyncio
    async def test_login_by_device_id(self, test_service: UserService, test_data: User, expect_data: User):
        get_data = await test_service.login_by_device_id(test_data.device_id)
        assert get_data.device_id == expect_data.device_id

    @pytest.mark.asyncio
    async def test_register_user_by_email(self, test_service: UserService, test_data: User, expect_data: User):
        get_data = await test_service.register_user_by_email(test_data.email, test_data.password)
        assert get_data.email == expect_data.email

    @pytest.mark.asyncio
    async def test_login_by_email(self, test_service: UserService, test_data: User, expect_data: User):
        get_data = await test_service.login_by_email(test_data.email, test_data.password)
        assert get_data.email == expect_data.email

    @pytest.mark.asyncio
    async def test_check_user_by_email(self, test_service: UserService, test_data: User, expect_data: User):
        get_data = await test_service.check_user_by_email(test_data.email)
        assert get_data.email == expect_data.email

    @pytest.mark.asyncio
    async def test_check_user_by_device_id(self, test_service: UserService, test_data: User, expect_data: User):
        get_data = await test_service.check_user_by_device_id(test_data.device_id)
        assert get_data.device_id == expect_data.device_id

    @pytest.mark.asyncio
    async def test_update_user(self, test_service: UserService, test_data: User, expect_data: User):
        get_data = await test_service.check_user_by_device_id(test_data.device_id)
        get_data.display_name = expect_data.display_name
        update_data = await test_service.update_user(get_data.id, get_data)
        assert update_data.display_name == expect_data.display_name

    @pytest.mark.asyncio
    async def test_delete_users(self, test_service: UserService):
        users = [await test_service.register_user_by_device_id(uuid4()) for _ in range(10)]
        pass_user_ids = [user.id for user in users]
        fail_user_ids = pass_user_ids + [1000]

        is_delete_success = await test_service.delete_users(fail_user_ids)
        assert is_delete_success == False

        is_delete_success = await test_service.delete_users(pass_user_ids)
        assert is_delete_success == True


class TestConsoleUserService:
    @pytest.fixture(scope='class')
    def test_service(self, async_session) -> ConsoleUserService:
        return ConsoleUserService(session=async_session)

    @pytest.fixture(scope='class')
    def test_data(self):
        return ConsoleUser(email='test_email@email.com', password='test_password', user_name='test_name')

    @pytest.fixture(scope='class')
    def expect_data(self):
        return ConsoleUser(email='test_email@email.com', password='test_password', user_name='update_name')

    @pytest.mark.asyncio
    async def test_register_console_user(self, test_service: ConsoleUserService, test_data: ConsoleUser, expect_data: ConsoleUser):
        get_data = await test_service.register_console_user(test_data.email, test_data.password, role=Role.OWNER)
        assert get_data.email == expect_data.email

    @pytest.mark.asyncio
    async def test_login_by_email(self, test_service: ConsoleUserService, test_data: ConsoleUser, expect_data: ConsoleUser):
        get_data = await test_service.login_by_email(test_data.email, test_data.password)
        assert get_data.email == expect_data.email

    @pytest.mark.asyncio
    async def test_get_console_user_by_id(self, test_service: ConsoleUserService, test_data: ConsoleUser):
        base_data = await test_service.login_by_email(test_data.email, test_data.password)
        get_data = await test_service.get_console_user_by_id(base_data.id)
        assert get_data.id == base_data.id

    @pytest.mark.asyncio
    async def test_update_console_user(self, test_service: ConsoleUserService, test_data: ConsoleUser, expect_data: ConsoleUser):
        get_data = await test_service.login_by_email(test_data.email, test_data.password)
        get_data.user_name = expect_data.user_name
        update_data = await test_service.update_console_user(get_data.id, get_data)
        assert update_data.user_name == expect_data.user_name

    @pytest.mark.asyncio
    async def test_delete_console_users(self, test_service: ConsoleUserService):
        owner_users = [
            await test_service.register_console_user(email=uuid4(), password=uuid4(), role=Role.MAINTAINER)for _ in range(10)
        ]
        pass_user_ids = [user.id for user in owner_users]
        fail_user_ids = pass_user_ids + [1000]

        is_delete_success = await test_service.delete_console_users(fail_user_ids)
        assert is_delete_success == False

        is_delete_success = await test_service.delete_console_users(pass_user_ids)
        assert is_delete_success == True

    @pytest.mark.asyncio
    async def test_check_last_console_owner_for_update(self, test_service: ConsoleUserService, test_data: ConsoleUser):
        base_data = await test_service.login_by_email(test_data.email, test_data.password)
        is_last = await test_service.check_last_console_owner_for_update(base_data.id)
        assert is_last == True

    @pytest.mark.asyncio
    async def test_check_last_console_owner_for_delete(self, test_service: ConsoleUserService):
        owner_users = [
            await test_service.register_console_user(email=uuid4(), password=uuid4(), role=Role.OWNER)for _ in range(10)
        ]
        pass_user_ids = [user.id for user in owner_users]
        fail_user_ids = pass_user_ids + [1]

        is_last = await test_service.check_last_console_owner_for_delete(pass_user_ids)
        assert is_last == False

        is_last = await test_service.check_last_console_owner_for_delete(fail_user_ids)
        assert is_last == True

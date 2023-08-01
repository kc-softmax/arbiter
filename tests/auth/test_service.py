import pytest
from uuid import uuid4

from server.auth.models import ConsoleUser, User, Role
from server.auth.service import ConsoleUserService, UserService


class TestUserService:
    @pytest.fixture(scope='class')
    def test_service(self, async_session) -> UserService:
        return UserService(session=async_session)

    @pytest.fixture(scope='class')
    def test_data_for_login_device_id(self):
        return User(device_id='test_device_id')

    @pytest.fixture(scope='class')
    def test_data_for_login_email(self):
        return User(email='test_email@email.com', password='test_password')

    @pytest.fixture(scope='class')
    def test_data_for_update(self):
        return User(
            display_name='test_display_name',
            access_token='test_access_token',
            refresh_token='test_refresh_token'
        )

    @pytest.mark.asyncio
    async def test_register_user_by_device_id(self, test_service: UserService, test_data_for_login_device_id: User):
        register_data = await test_service.register_user_by_device_id(test_data_for_login_device_id.device_id)
        assert register_data.device_id == test_data_for_login_device_id.device_id

    @pytest.mark.asyncio
    async def test_login_by_device_id(self, test_service: UserService, test_data_for_login_device_id: User):
        login_data = await test_service.login_by_device_id(test_data_for_login_device_id.device_id)
        assert login_data.device_id == test_data_for_login_device_id.device_id

    @pytest.mark.asyncio
    async def test_register_user_by_email(self, test_service: UserService, test_data_for_login_email: User):
        register_data = await test_service.register_user_by_email(
            test_data_for_login_email.email,
            test_data_for_login_email.password
        )
        assert register_data.email == test_data_for_login_email.email

    @pytest.mark.asyncio
    async def test_login_by_email(self, test_service: UserService, test_data_for_login_email: User):
        login_data = await test_service.login_by_email(
            test_data_for_login_email.email,
            test_data_for_login_email.password
        )
        assert login_data.email == test_data_for_login_email.email

    @pytest.mark.asyncio
    async def test_check_user_by_email(self, test_service: UserService, test_data_for_login_email: User):
        get_data = await test_service.check_user_by_email(test_data_for_login_email.email)
        assert get_data.email == test_data_for_login_email.email

    @pytest.mark.asyncio
    async def test_check_user_by_device_id(self, test_service: UserService, test_data_for_login_device_id: User):
        get_data = await test_service.check_user_by_device_id(test_data_for_login_device_id.device_id)
        assert get_data.device_id == test_data_for_login_device_id.device_id

    @pytest.mark.asyncio
    async def test_user_update(self, test_service: UserService, test_data_for_login_email: User, test_data_for_update: User):
        get_user = await test_service.check_user_by_email(test_data_for_login_email.email)
        # 값비교를 위해 instance를 session에서 분리
        test_service.session.expunge(get_user)
        update_user = await test_service.update_user(
            get_user.id,
            test_data_for_update
        )
        # update 필드와 update 대상이 아닌 필드 분리
        update_fields = update_user.dict(exclude_unset=True).keys()
        not_update_fields = User.__fields__.keys() - update_fields

        # update 대상 항목 값 비교
        for key in update_fields:
            assert getattr(update_user, key) == getattr(test_data_for_update, key)

        # update 대상이 아닌 항목 값 비교
        for key in not_update_fields:
            assert getattr(update_user, key) == getattr(get_user, key)

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
    @pytest.fixture(scope='class')
    def test_service(self, async_session) -> ConsoleUserService:
        return ConsoleUserService(session=async_session)

    @pytest.fixture(scope='class')
    def test_data_for_login_email(self):
        return ConsoleUser(email='test_email@email.com', password='test_password', role=Role.OWNER)

    @pytest.fixture(scope='class')
    def test_data_for_update(self):
        return ConsoleUser(user_name='test_user_name', deprecated=True)

    @pytest.mark.asyncio
    async def test_register_console_user(self, test_service: ConsoleUserService, test_data_for_login_email: ConsoleUser):
        get_data = await test_service.register_console_user(
            test_data_for_login_email.email,
            test_data_for_login_email.password,
            test_data_for_login_email.role
        )
        assert get_data.email == test_data_for_login_email.email

    @pytest.mark.asyncio
    async def test_login_by_email(self, test_service: ConsoleUserService, test_data_for_login_email: ConsoleUser):
        get_data = await test_service.login_by_email(
            test_data_for_login_email.email, test_data_for_login_email.password
        )
        assert get_data.email == test_data_for_login_email.email

    @pytest.mark.asyncio
    async def test_get_console_user_by_id(self, test_service: ConsoleUserService, test_data_for_login_email: ConsoleUser):
        base_data = await test_service.login_by_email(
            test_data_for_login_email.email, test_data_for_login_email.password
        )
        get_data = await test_service.get_console_user_by_id(base_data.id)
        assert get_data.id == base_data.id

    @pytest.mark.asyncio
    async def test_update_console_user(
        self,
        test_service: ConsoleUserService,
        test_data_for_login_email: ConsoleUser,
        test_data_for_update: ConsoleUser
    ):
        get_user = await test_service.login_by_email(
            test_data_for_login_email.email,
            test_data_for_login_email.password
        )
        # 값비교를 위해 instance를 session에서 분리
        test_service.session.expunge(get_user)

        update_user = await test_service.update_console_user(
            get_user.id,
            test_data_for_update
        )
        # update 필드와 update 대상이 아닌 필드 분리
        update_fields = update_user.dict(exclude_unset=True).keys()
        not_update_fields = ConsoleUser.__fields__.keys() - update_fields

        # update 대상 항목 비교
        for key in update_fields:
            assert getattr(update_user, key) == getattr(test_data_for_update, key)

        # update 대상이 아닌 항목 값 비교
        for key in not_update_fields:
            assert getattr(update_user, key) == getattr(get_user, key)

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
        test_data_for_login_email: ConsoleUser
    ):
        base_data = await test_service.login_by_email(
            test_data_for_login_email.email,
            test_data_for_login_email.password
        )
        is_last = await test_service.check_last_console_owner_for_update(base_data.id)
        assert is_last == True

    @pytest.mark.asyncio
    async def test_check_last_console_owner_for_delete(self, test_service: ConsoleUserService):
        # 테스트용 유저 생성
        owner_users = [
            await test_service.register_console_user(
                email=uuid4(), password=uuid4(), role=Role.OWNER
            ) for _ in range(10)
        ]
        # 성공 테스트를 위해 생성한 유저 id 추가
        pass_user_ids = [user.id for user in owner_users]
        # 실패 테스트를 위해 먼저 생성된 owner id 추가
        fail_user_ids = pass_user_ids + [1]

        is_last = await test_service.check_last_console_owner_for_delete(pass_user_ids)
        assert is_last == False

        is_last = await test_service.check_last_console_owner_for_delete(fail_user_ids)
        assert is_last == True

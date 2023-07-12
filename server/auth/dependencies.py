from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from server.database import get_async_session
from server.auth.models import User, ConsoleUser, ConsoleRole
from server.auth.service import ConsoleUserService, UserService
from server.auth.exceptions import InvalidToken, NotFoundUser, AuthorizationFailed
from server.auth.utils import verify_token


def get_user_service(
    session: AsyncSession = Depends(get_async_session)
) -> UserService:
    return UserService(session=session)


def get_console_user_service(
    session: AsyncSession = Depends(get_async_session)
) -> ConsoleUserService:
    # TODO generic으로 합치기
    return ConsoleUserService(session=session)


async def get_current_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login")),
    user_service: UserService = Depends(get_user_service)
) -> User:
    ''' 
    # jwt 토큰을 디코딩하여 현재 auth 정보를 불러온다.
    토큰은 이름(subject), 유효기간(exp), 로그인 방식(login_type) 데이터로 이루어진다.
    그리고 로그인 방식에 따라 각각의 방식으로 요청하여 유저 정보를 가져온다.
    이 때 유저가 없거나 저장된 토큰과 헤더에 담겨 온 토큰이 다를 경우, 예외를 발생시킨다.
    (저장된 토큰과 헤더에 담겨 온 토큰이 다르다는 것은 이미 deprecated된 토큰으로 요청을 보냈다는 뜻)
    '''
    token_data = verify_token(token)
    user = await user_service.get_user(token_data.sub)
    if user is None:
        raise NotFoundUser
    # 저장된 액세스토큰과 같은 토큰인지 확인
    if user.access_token != token:
        raise InvalidToken
    return user


async def get_current_console_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/console/login")),
    user_service: ConsoleUserService = Depends(get_console_user_service)
) -> ConsoleUser:
    token_data = verify_token(token)
    user = await user_service.get_console_user_by_id(token_data.sub)
    if user is None:
        raise NotFoundUser
    if user.access_token != token:
        raise InvalidToken
    return user


class ConsoleRoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, console_user: ConsoleUser = Depends(get_current_console_user)):
        if console_user.role not in self.allowed_roles:
            raise AuthorizationFailed
        return console_user


allowed_only_for_owner = ConsoleRoleChecker([ConsoleRole.OWNER])

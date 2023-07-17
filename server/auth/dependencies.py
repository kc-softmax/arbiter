from datetime import datetime
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2AuthorizationCodeBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from server.config import settings
from server.database import get_async_session
from server.auth.models import User, Role, LoginType
from server.auth.constants import TOKEN_GENERATE_ALGORITHM
from server.auth.schemas import TokenDataSchema
from server.auth.service import ConsoleUserService, PaginationService, UserService
from server.auth.exceptions import InvalidToken, AuthorizationFailed, NotFoundUser, InvalidCredentials


def get_user_service(
    session: AsyncSession = Depends(get_async_session)
) -> UserService:
    return UserService(session=session)


def get_console_user_service(
    session: AsyncSession = Depends(get_async_session)
) -> ConsoleUserService:
    return ConsoleUserService(session=session)


def get_pagination_service(
    session: AsyncSession = Depends(get_async_session)
) -> PaginationService:
    return PaginationService(session=session)


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
    try:
        payload = jwt.decode(
            token, settings.JWT_ACCESS_SECRET_KEY, algorithms=[TOKEN_GENERATE_ALGORITHM.HS256]
        )
        token_data = TokenDataSchema(
            sub=payload.get("sub"),
            exp=payload.get("exp"),
            login_type=LoginType(payload.get("login_type"))
        )
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise InvalidToken
    except (JWTError, ValidationError):
        raise InvalidCredentials

    user = None
    match token_data.login_type:
        case LoginType.EMAIL:
            user = await user_service.check_user_by_email(token_data.sub)
        case LoginType.GUEST:
            user = await user_service.check_user_by_device_id(token_data.sub)
    if user is None:
        raise NotFoundUser
    # 저장된 액세스토큰과 같은 토큰인지 확인
    if user.access_token != token:
        raise InvalidToken
    return user


class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise AuthorizationFailed
        return user


allowed_only_for_admin = RoleChecker([Role.OWNER, Role.MAINTAINER])
allowed_only_for_gamer = RoleChecker([Role.GAMER])

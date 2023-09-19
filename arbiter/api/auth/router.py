import uuid
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from http import HTTPStatus
from enum import StrEnum

import arbiter.api.auth.exceptions as AuthExceptions
import arbiter.api.auth.schemas as AuthSchemas
from arbiter.api.auth.models import LoginType, User
from arbiter.api.auth.dependencies import get_current_user
from arbiter.api.auth.utils import (
    create_token,
    verify_token as verify_token_util,
    get_password_hash,
    verify_password,
)
from arbiter.api.exceptions import BadRequest
from arbiter.api.database import UnitOfWork
from arbiter.api.dependencies import get_uow


router = APIRouter(prefix="/auth")


class AuthRouterTag(StrEnum):
    TOKEN = "Token"
    GAMER = "Auth(game)"


@router.post(
    "/token/verify",
    tags=[AuthRouterTag.TOKEN],
    response_model=bool
)
async def verify_token(
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="")),
        uow: UnitOfWork = Depends(get_uow),
):
    try:
        token_data = verify_token_util(token)
    except AuthExceptions.InvalidToken:
        return False

    user = await uow.gamer_users.get_by_id(token_data.sub)
    if user == None or user.access_token != token:
        return False
    return True


@router.post(
    "/token/refresh",
    tags=[AuthRouterTag.TOKEN],
    response_model=AuthSchemas.TokenSchema
)
async def refresh_token(
    data: AuthSchemas.TokenRefreshRequest,
    uow: UnitOfWork = Depends(get_uow),
):
    token_data = verify_token_util(data.refresh_token, True)
    # DB에 저장된 토큰과 같은 토큰인 지 확인
    user = await uow.gamer_users.get_by_id(token_data.sub)
    if user == None or data.access_token != user.access_token or data.refresh_token != user.refresh_token:
        raise AuthExceptions.InvalidToken

    # 새로운 토큰 발급
    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user.access_token = new_token.access_token
    user.refresh_token = new_token.refresh_token
    await uow.gamer_users.update(user)
    return new_token


@router.post(
    "/game/signup/email",
    tags=[AuthRouterTag.GAMER],
    status_code=HTTPStatus.CREATED,
    response_model=AuthSchemas.GamerUserSchema
)
# 이메일 게이머 가입
async def signup_email(
    data: AuthSchemas.GamerUserCreateByEmail,
    uow: UnitOfWork = Depends(get_uow),
):
    user = await uow.gamer_users.get_one_by(email=data.email)
    if user != None:
        raise AuthExceptions.UserAlready
    user = await uow.gamer_users.add(
        User(
            email=data.email,
            password=get_password_hash(data.password),
            login_type=LoginType.EMAIL,
        )
    )
    return user


@router.post(
    '/game/login/email',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
# 이메일 게이머 로그인
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    uow: UnitOfWork = Depends(get_uow),
):
    user = await uow.gamer_users.get_one_by(email=form_data.username)
    if user == None:
        raise AuthExceptions.NotFoundUser
    if not verify_password(form_data.password, user.password):
        raise AuthExceptions.InvalidCredentials

    token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user.access_token = token.access_token
    user.refresh_token = token.refresh_token
    await uow.gamer_users.update(user)
    return user


@router.post(
    "/game/signup/guest",
    tags=[AuthRouterTag.GAMER],
    status_code=HTTPStatus.CREATED,
    response_model=AuthSchemas.GamerUserSchema
)
# 게스트 게이머 가입
async def signup_guest(uow: UnitOfWork = Depends(get_uow),):
    # 임의의 id 생성
    device_id = uuid.uuid4()
    user: User = await uow.gamer_users.add(
        User(
            device_id=str(device_id),
            login_type=LoginType.GUEST,
        )
    )
    return user


@router.post(
    "/game/login/guest",
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.TokenSchema
)
# 게스트 게이머 로그인
async def login_guest(
    data: AuthSchemas.GamerUserLoginByGuest,
    uow: UnitOfWork = Depends(get_uow),
):
    user = await uow.gamer_users.get_one_by(device_id=data.device_id)
    if user == None:
        raise BadRequest
    token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user.access_token = token.access_token
    user.refresh_token = token.refresh_token
    await uow.gamer_users.update(user)
    return user


@router.post(
    '/game/me',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.delete(
    '/game/me',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
async def leave(
    user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
):
    await uow.gamer_users.delete(user.id)
    return user


@router.patch(
    '/game/me',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
# 게이머 본인 정보 수정
async def update_user_info(
        data: AuthSchemas.GamerUserUpdate,
        user: User = Depends(get_current_user),
        uow: UnitOfWork = Depends(get_uow),
):
    user.user_name = data.user_name
    await uow.gamer_users.update(user)
    return user

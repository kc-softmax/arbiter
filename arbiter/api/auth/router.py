import uuid
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from http import HTTPStatus
from enum import Enum

import arbiter.api.auth.exceptions as AuthExceptions
import arbiter.api.auth.schemas as AuthSchemas
from arbiter.api.auth.repository import game_uesr_repository
from arbiter.api.auth.models import LoginType, GameUser
from arbiter.api.auth.dependencies import get_current_user
from arbiter.api.auth.utils import (
    create_token,
    verify_token as verify_token_util,
    get_password_hash,
    verify_password,
)
from arbiter.api.exceptions import BadRequest
from arbiter.api.dependencies import unit_of_work
from arbiter.api.game_tester import GameTesterAPI

class AuthRouterTag(str, Enum):
    TOKEN = "Token"
    GAMER = "Auth(game)"

repositories = [game_uesr_repository]
router = APIRouter(
    prefix="/auth",
)


@router.post(
    "/token/verify",
    tags=[AuthRouterTag.TOKEN],
    response_model=bool
)
async def verify_token(session: AsyncSession = Depends(unit_of_work), token: str = Depends(OAuth2PasswordBearer(tokenUrl=""))):
    try:
        token_data = verify_token_util(token)
    except AuthExceptions.InvalidToken:
        return False

    user = await game_uesr_repository.get_by_id(session, int(token_data.sub))
    if user == None or user.access_token != token:
        return False
    return True


@router.post(
    "/token/refresh",
    tags=[AuthRouterTag.TOKEN],
    response_model=AuthSchemas.TokenSchema
)
async def refresh_token(data: AuthSchemas.TokenRefreshRequest, session: AsyncSession = Depends(unit_of_work)):
    token_data = verify_token_util(data.refresh_token, True)
    # DB에 저장된 토큰과 같은 토큰인 지 확인
    user = await game_uesr_repository.get_by_id(session, int(token_data.sub))
    if user == None or data.access_token != user.access_token or data.refresh_token != user.refresh_token:
        raise AuthExceptions.InvalidToken

    # 새로운 토큰 발급
    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user.access_token = new_token.access_token
    user.refresh_token = new_token.refresh_token
    await game_uesr_repository.update(session, user)
    return new_token


@router.post(
    "/game/signup/email",
    tags=[AuthRouterTag.GAMER],
    status_code=HTTPStatus.CREATED,
    response_model=AuthSchemas.GamerUserSchema
)
# 이메일 게이머 가입
async def signup_email(data: AuthSchemas.GamerUserCreateByEmail, session: AsyncSession = Depends(unit_of_work)):
    user = await game_uesr_repository.get_one_by(session, email=data.email)
    if user != None:
        raise AuthExceptions.UserAlready
    user = await game_uesr_repository.add(
        session,
        GameUser(
            user_name=data.user_name,
            email=data.email,
            password=get_password_hash(data.password),
            login_type=LoginType.EMAIL,
            adapter=data.adapter,
        )
    )
    return user


@router.post(
    '/game/login/email',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
# 이메일 게이머 로그인
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(unit_of_work)):
    user = await game_uesr_repository.get_one_by(session, email=form_data.username)
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
    await game_uesr_repository.update(session, user)
    return user


@router.post(
    "/game/signup/guest",
    tags=[AuthRouterTag.GAMER],
    status_code=HTTPStatus.CREATED,
    response_model=AuthSchemas.GamerUserSchema
)
# 게스트 게이머 가입
async def signup_guest(
    session: AsyncSession = Depends(unit_of_work)
):
    # 임의의 id 생성
    device_id = uuid.uuid4()
    user = await game_uesr_repository.add(
        session,
        GameUser(
            device_id=str(device_id),
            login_type=LoginType.GUEST,
        )
    )
    return user

@router.post(
    "/game/login/username",
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
# Temp 게임 테스터 게이머 가입 및 로그인
async def login_user_name(data: AuthSchemas.GamerUserLoginByUserName, session: AsyncSession = Depends(unit_of_work)):    
    user = await game_uesr_repository.get_one_by(session, user_name=data.user_name)
    if user == None:
        player_token = None
        player_name = None
        if not data.user_name.startswith("so_"):
            result = await GameTesterAPI().auth(data.user_name)
            if result is None or result["code"] != -1:
                raise AuthExceptions.BadRequest
            player_token = result["playerToken"]
            player_name = result["playerName"]
            
        user = await game_uesr_repository.add(
            session,
            GameUser(
                user_name=data.user_name,
                player_token=player_token,
                player_name = player_name,
                login_type=LoginType.TESTER
            )
        )
        
    token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user.access_token = token.access_token
    user.refresh_token = token.refresh_token
    await game_uesr_repository.update(session, user)

    return user


@router.post(
    "/game/login/guest",
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
# 게스트 게이머 로그인
async def login_guest(data: AuthSchemas.GamerUserLoginByGuest, session: AsyncSession = Depends(unit_of_work)):
    user = await game_uesr_repository.get_one_by(session, device_id=data.device_id)
    if user == None:
        raise BadRequest
    token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user.access_token = token.access_token
    user.refresh_token = token.refresh_token
    await game_uesr_repository.update(session, user)
    return user


@router.post(
    '/game/me',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
async def get_me(user: GameUser = Depends(get_current_user)):
    return user


@router.delete(
    '/game/me',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
async def leave(user: GameUser = Depends(get_current_user), session: AsyncSession = Depends(unit_of_work)):
    await game_uesr_repository.delete(session, user.id)
    return user


@router.patch(
    '/game/me',
    tags=[AuthRouterTag.GAMER],
    response_model=AuthSchemas.GamerUserSchema
)
# 게이머 본인 정보 수정
async def update_me_info(
        data: AuthSchemas.GamerUserUpdate,
        user: GameUser = Depends(get_current_user),
        session: AsyncSession = Depends(unit_of_work)
):
    user.user_name = data.user_name
    await game_uesr_repository.update(session, user)
    return user

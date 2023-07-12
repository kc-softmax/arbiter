import uuid
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from http import HTTPStatus
from sqlalchemy.ext.asyncio import AsyncSession
from enum import StrEnum

from server.database import get_async_session
from server.exceptions import BadRequest
from server.pagination import PaginationRequest, PaginationResponse, create_pagination
from server.auth.models import ConsoleUser, User
from server.auth.service import ConsoleUserService, UserService
from server.auth.utils import create_token, verify_token as verify_token_util, get_password_hash, verify_password, list_string_to_list
from server.auth.dependencies import get_console_user_service, get_user_service, get_current_user, get_current_console_user, allowed_only_for_owner
from server.auth.exceptions import (AtLeastOneOwner, UserAlready,
                                    InvalidCredentials, InvalidToken,
                                    NotFoundUser, NotFoundUserForDelete,
                                    NotFoundUserForUpdate)
from server.auth.schemas import (ConsoleUserCreate, ConsoleUserGet,
                                 ConsoleUserUpdate, GamerUserCreateByEmail,
                                 GamerUserLoginByGuest, GamerUserSchema,
                                 GamerUserUpdate, TokenRefreshRequest,
                                 TokenSchema, ConsoleUserSchema,
                                 ConsoleRequest)

router = APIRouter(prefix="/auth")


class AuthRouterTag(StrEnum):
    TOKEN = "Token"
    GAMER = "Auth(game)"
    CONSOLE = "Auth(console)"


@router.post("/token/verify",
             tags=[AuthRouterTag.TOKEN],
             response_model=bool)
async def verify_token(data: ConsoleRequest,
                       token: str = Depends(OAuth2PasswordBearer(tokenUrl="")),
                       user_service: UserService = Depends(get_user_service),
                       console_user_service: ConsoleUserService = Depends(get_console_user_service)):
    token_data = None
    try:
        token_data = verify_token_util(token)
    except:
        return False

    user = None
    if data.is_console:
        user = await console_user_service.get_console_user_by_id(token_data.sub)
    else:
        user = await user_service.get_user(token_data.sub)
    if user == None or token != user.access_token:
        return False

    return True


@router.post("/token/refresh",
             tags=[AuthRouterTag.TOKEN],
             response_model=TokenSchema)
async def refresh_token(data: TokenRefreshRequest,
                        user_service: UserService = Depends(get_user_service),
                        console_user_service: ConsoleUserService = Depends(get_console_user_service)):

    token_data = verify_token_util(data.refresh_token, True)

    # DB에 저장된 토큰과 같은 토큰인 지 확인
    user = None
    if data.is_console:
        user = await console_user_service.get_console_user_by_id(token_data.sub)
    else:
        user = await user_service.get_user(token_data.sub)
    if user == None or data.access_token != user.access_token or data.refresh_token != user.refresh_token:
        raise InvalidToken

    # 새로운 토큰 발급
    new_token = TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    if data.is_console:
        await console_user_service.update_console_user(user.id, ConsoleUser(**new_token.dict()))
    else:
        await user_service.update_user(user.id, User(**new_token.dict()))
    return new_token


@router.post("/game/signup/email",
             tags=[AuthRouterTag.GAMER],
             status_code=HTTPStatus.CREATED,
             response_model=GamerUserSchema)
# 이메일 게이머 가입
async def signup_email(data: GamerUserCreateByEmail, user_service: UserService = Depends(get_user_service)):
    user = await user_service.check_user_by_email(data.email)
    if user is not None:
        raise UserAlready
    user = await user_service.register_user_by_email(data.email, get_password_hash(data.password))
    return user


@router.post('/game/login/email',
             tags=[AuthRouterTag.GAMER],
             response_model=TokenSchema)
# 이메일 게이머 로그인
async def login(form_data: OAuth2PasswordRequestForm = Depends(), user_service: UserService = Depends(get_user_service)):
    user = await user_service.check_user_by_email(form_data.username)
    if user is None:
        raise NotFoundUser
    if not verify_password(form_data.password, user.password):
        raise InvalidCredentials

    token = TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )

    # 로그인 시, 갱신한 토큰을 DB에 저장
    await user_service.update_user(user.id, User(**token.dict()))
    return token


@router.post("/game/signup/guest",
             tags=[AuthRouterTag.GAMER],
             status_code=HTTPStatus.CREATED,
             response_model=GamerUserSchema)
# 게스트 게이머 가입
async def signup_guest(user_service: UserService = Depends(get_user_service)):
    # 임의의 id 생성
    device_id = uuid.uuid4()
    user = await user_service.register_user_by_device_id(str(device_id))
    return user


@router.post("/game/login/guest",
             tags=[AuthRouterTag.GAMER],
             response_model=TokenSchema)
# 게스트 게이머 로그인
async def login_guest(data: GamerUserLoginByGuest, user_service: UserService = Depends(get_user_service)):
    user = await user_service.login_by_device_id(data.device_id)
    if user is None:
        raise BadRequest
    token = TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    await user_service.update_user(user.id, User(**token.dict()))
    return token


@router.post('/game/me',
             tags=[AuthRouterTag.GAMER],
             response_model=GamerUserSchema)
async def get_me(user: User = Depends(get_current_user)):
    if user is None:
        raise NotFoundUser
    return user


@router.delete('/game/me',
               tags=[AuthRouterTag.GAMER],
               response_model=GamerUserSchema)
async def leave(user: User = Depends(get_current_user), user_service: UserService = Depends(get_user_service)):
    if not await user_service.delete_user(user.id):
        raise NotFoundUser
    return user


@router.patch('/game/me',
              tags=[AuthRouterTag.GAMER],
              response_model=GamerUserSchema)
# 게이머 본인 정보 수정
async def update_user_info(data: GamerUserUpdate, user: User = Depends(get_current_user), user_service: UserService = Depends(get_user_service)):
    user = await user_service.update_user(user.id, User(**data.dict()))
    if user is None:
        raise NotFoundUser
    return user


@router.post("/console/signup",
             tags=[AuthRouterTag.CONSOLE],
             status_code=HTTPStatus.CREATED,
             response_model=ConsoleUserSchema,
             dependencies=[Depends(get_current_console_user)])
# 이메일 메인테이너 생성
async def signup_console(data: ConsoleUserCreate, console_user_service: ConsoleUserService = Depends(get_console_user_service)):
    console_user = await console_user_service.get_console_user_by_email(data.email)
    if console_user is not None:
        raise UserAlready
    console_user = await console_user_service.register_console_user(
        email=data.email,
        password=get_password_hash(data.password),
        user_name=data.user_name,
        role=data.role
    )
    return console_user


@router.post('/console/login',
             tags=[AuthRouterTag.CONSOLE],
             response_model=TokenSchema)
# 콘솔 유저 로그인
async def login_console(form_data: OAuth2PasswordRequestForm = Depends(), console_user_service: ConsoleUserService = Depends(get_console_user_service)):
    console_user = await console_user_service.get_console_user_by_email(form_data.username)
    if console_user is None:
        raise BadRequest
    if not verify_password(form_data.password, console_user.password):
        raise BadRequest

    token = TokenSchema(
        access_token=create_token(console_user.id),
        refresh_token=create_token(console_user.id, True)
    )
    # 로그인 시, 갱신한 토큰을 DB에 저장
    await console_user_service.update_console_user(console_user.id, ConsoleUser(**token.dict()))
    return token


@router.post('/console/me',
             tags=[AuthRouterTag.CONSOLE],
             response_model=ConsoleUserSchema)
async def get_me(console_user: ConsoleUser = Depends(get_current_console_user)):
    if console_user is None:
        raise NotFoundUser
    return console_user


@router.post('/console/list/console-user',
             tags=[AuthRouterTag.CONSOLE],
             response_model=PaginationResponse[ConsoleUserSchema],
             dependencies=[Depends(get_current_console_user)])
# 메인테이너 리스트 불러오기
async def get_console_user_list(
    data: PaginationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    return await create_pagination(
        session,
        ConsoleUser,
        ConsoleUserSchema,
        data
    )


@router.post('/console/console-user',
             tags=[AuthRouterTag.CONSOLE],
             response_model=ConsoleUserSchema,
             dependencies=[Depends(get_current_console_user)])
# 메인테이너 1명 불러오기
async def get_console_user(data: ConsoleUserGet, console_user_service: ConsoleUserService = Depends(get_console_user_service)):
    console_user = await console_user_service.get_console_user_by_id(data.id)
    if console_user is None:
        raise NotFoundUser
    return console_user


@router.patch('/console/console-user',
              tags=[AuthRouterTag.CONSOLE],
              response_model=ConsoleUserSchema,
              dependencies=[Depends(allowed_only_for_owner)])
# 메인테이너 수정(권한: 오너)
async def update_console_user(data: ConsoleUserUpdate, console_user_service: ConsoleUserService = Depends(get_console_user_service)):
    if await console_user_service.check_last_console_owner_for_update(data.id):
        raise AtLeastOneOwner

    console_user = await console_user_service.update_console_user(data.id, ConsoleUser(**data.dict(exclude_unset=True)))
    if console_user is None:
        raise NotFoundUserForUpdate
    return console_user


@router.delete('/console/console-user/{ids}',
               tags=[AuthRouterTag.CONSOLE],
               response_model=bool,
               dependencies=[Depends(allowed_only_for_owner)])
# 메인테이너 단일 삭제 / 복수 삭제(권한: 오너)
async def delete_console_user(
    ids: str,
    console_user_service: ConsoleUserService = Depends(get_console_user_service)
):
    ids = list_string_to_list(ids)
    if ids is None or len(ids) == 0:
        raise BadRequest
    if await console_user_service.check_last_console_owner_for_delete(ids):
        raise AtLeastOneOwner

    # 삭제 대상이 없거나 에러가 있을 경우, rollback and False
    is_success = await console_user_service.delete_console_users(ids)
    if not is_success:
        raise NotFoundUserForDelete
    return True


@router.post('/console/list/gamer-user',
             tags=[AuthRouterTag.CONSOLE],
             response_model=PaginationResponse[GamerUserSchema],
             dependencies=[Depends(get_current_console_user)])
# 게이머 리스트 불러오기
async def get_gamer_user_list(
    data: PaginationRequest,
    session: AsyncSession = Depends(get_async_session)
):
    return await create_pagination(
        session,
        User,
        GamerUserSchema,
        data
    )

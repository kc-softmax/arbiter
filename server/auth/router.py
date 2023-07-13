from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from http import HTTPStatus
from datetime import timedelta
import uuid

from server.config import settings
from server.exceptions import BadRequest
from server.auth.models import User, LoginType
from server.auth.schemas import CreateEmailUserRequest, UserSchema, TokenSchema, UpdateUserRequest, LoginGuestUserRequest
from server.auth.service import UserService, ConsoleUserService
from server.auth.utils import create_token
from server.auth.exceptions import UserAlready, InvalidCredentials, InvalidToken, NotFoundUser, AuthorizationFailed
from server.auth.dependencies import get_user_service, allowed_only_for_gamer, get_console_user_service
from server.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES


router = APIRouter(prefix="/auth")


@router.post("/signup/email",
             status_code=HTTPStatus.CREATED,
             response_model=UserSchema,
             responses={**UserAlready.to_openapi_response()})
# 이메일 게이머 가입
async def signup_email(data: CreateEmailUserRequest, user_service: UserService = Depends(get_user_service)):
    user = await user_service.check_user_by_email(data.email)
    if user is not None:
        raise UserAlready
    user = await user_service.register_user_by_email(data.email, data.password)
    return UserSchema(**user.dict())


@router.post('/login/email',
             response_model=TokenSchema,
             responses={**InvalidCredentials.to_openapi_response()})
# 이메일 게이머 로그인
async def login(form_data: OAuth2PasswordRequestForm = Depends(), user_service: UserService = Depends(get_user_service)):
    user = await user_service.login_by_email(form_data.username, form_data.password)
    if user is None:
        raise InvalidCredentials
    token = TokenSchema(
        access_token=create_token(user.email,
                                  LoginType.EMAIL,
                                  settings.JWT_ACCESS_SECRET_KEY,
                                  timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
        refresh_token=create_token(user.email,
                                   LoginType.EMAIL,
                                   settings.JWT_REFRESH_SECRET_KEY,
                                   timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)))
    # 로그인 시, 갱신한 토큰을 DB에 저장
    await user_service.update_user(user.id, User(**token.dict()))
    return token


@router.post("/signup/guest",
             status_code=HTTPStatus.CREATED,
             response_model=UserSchema)
# 게스트 게이머 가입
async def signup_guest(user_service: UserService = Depends(get_user_service)):
    # 임의의 id 생성
    device_id = uuid.uuid4()
    user = await user_service.register_user_by_device_id(str(device_id))
    return user


@router.post("/login/guest",
             response_model=TokenSchema)
# 게스트 게이머 로그인
async def login_guest(data: LoginGuestUserRequest, user_service: UserService = Depends(get_user_service)):
    user = await user_service.login_by_device_id(data.device_id)
    if user is None:
        raise InvalidCredentials
    token = TokenSchema(
        access_token=create_token(data.device_id,
                                  LoginType.GUEST,
                                  settings.JWT_ACCESS_SECRET_KEY,
                                  timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
        refresh_token=create_token(data.device_id,
                                   LoginType.GUEST,
                                   settings.JWT_REFRESH_SECRET_KEY,
                                   timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)))
    await user_service.update_user(user.id, User(**token.dict()))
    return token


@router.get('/me',
            response_model=UserSchema,
            responses={**InvalidToken.to_openapi_response(),
                       **AuthorizationFailed.to_openapi_response(),
                       **NotFoundUser.to_openapi_response()})
async def get_me(user: User = Depends(allowed_only_for_gamer)):
    if user is None:
        raise BadRequest
    return UserSchema(**user.dict())


@router.post('/me/leave',
             response_model=UserSchema,
             responses={**InvalidToken.to_openapi_response(),
                        **AuthorizationFailed.to_openapi_response(),
                        **NotFoundUser.to_openapi_response()})
# 게이머 회원 탈퇴
# TODO
# 회원 탈퇴(삭제) 정책이 아직 미정.
# 만약 DB에서 삭제한다면 'DELETE' 요청도 고려
async def leave(user: User = Depends(allowed_only_for_gamer), user_service: UserService = Depends(get_user_service)):
    if not await user_service.delete_user(user.id):
        raise BadRequest
    return UserSchema(**user.dict())


@router.patch('/me/update',
              response_model=UserSchema,
              responses={**InvalidToken.to_openapi_response(),
                         **AuthorizationFailed.to_openapi_response(),
                         **NotFoundUser.to_openapi_response()})
# 게이머 본인 정보 수정
async def update_user_info(data: UpdateUserRequest, user: User = Depends(allowed_only_for_gamer), user_service: UserService = Depends(get_user_service)):
    user = await user_service.update_user(user.id, User(**data.dict()))
    if user is None:
        raise BadRequest
    return UserSchema(**user.dict())

# TODO
# 이메일 메인테이너 생성(권한: 오너)
# 메인테이너 수정 / 단일 삭제 / 복수 삭제(권한: 오너)
# 메인테이너 리스트 불러오기(권한: 오너, 메인테이너)
# 게이머 리스트 불러오기(권한: 오너, 메인테이너)
# 게이머 수정?(Ex_블럭처리)


@router.post("/login/console")
# 게스트 게이머 가입
async def signup_guest(console_user_service: ConsoleUserService = Depends(get_console_user_service)):
    # 임의의 id 생성
    user = await console_user_service.login_by_email(email='admin@admin.com', password='password')
    print('abcd', user)

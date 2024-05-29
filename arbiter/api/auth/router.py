import arbiter.api.auth.exceptions as AuthExceptions
import arbiter.api.auth.schemas as AuthSchemas
from prisma.errors import UniqueViolationError
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from http import HTTPStatus
from arbiter.api.auth.constants import AuthRouterTag
from arbiter.api.auth.utils import (
    create_token,
    verify_token as verify_token_util,
    get_password_hash,
    verify_password,
    generate_numeric_hash_tag
)
from arbiter.database import get_db, Prisma


router = APIRouter(
    prefix="/auth",
)


@router.post(
    "/token/verify",
    tags=[AuthRouterTag.TOKEN],
    response_model=bool
)
async def verify_token(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="")),
    db: Prisma = Depends(get_db)
):
    try:
        token_data = verify_token_util(token)
    except AuthExceptions.InvalidToken:
        return False

    user = await db.user.find_unique(where={"id": int(token_data.sub)})
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
    db: Prisma = Depends(get_db)
):
    token_data = verify_token_util(data.refresh_token, True)
    # DB에 저장된 토큰과 같은 토큰인 지 확인
    user = await db.user.find_unique(where={"id": int(token_data.sub)})
    if user == None or data.access_token != user.access_token or data.refresh_token != user.refresh_token:
        raise AuthExceptions.InvalidToken

    # 새로운 토큰 발급
    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    await db.user.update(
        where={"hash_tag": user.hash_tag},
        data=new_token.dict(exclude_unset=True)
    )
    return new_token


@router.post(
    "/signup/email",
    tags=[AuthRouterTag.USER],
    status_code=HTTPStatus.CREATED,
    response_model=AuthSchemas.UserResponse
)
# 이메일 게이머 가입
async def signup_email(
    data: AuthSchemas.UserCreate,
    db: Prisma = Depends(get_db)
):
    hashed_password = get_password_hash(data.password)
    hash_tag = generate_numeric_hash_tag(data.email)
    # AuthExceptions.UserAlreadyExists
    try:
        created_user = await db.user.create(
            data={
                "email": data.email,
                "password": hashed_password,
                "hash_tag": hash_tag,
            }
        )
    except UniqueViolationError:
        raise AuthExceptions.UserAlreadyExists
    except Exception as e:
        raise e

    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(created_user.id),
        refresh_token=create_token(created_user.id, True)
    )
    created_user = await db.user.update(
        where={"hash_tag": hash_tag},
        data=new_token.dict(exclude_unset=True)
    )
    return created_user


@router.post(
    '/login/email',
    tags=[AuthRouterTag.USER],
    response_model=AuthSchemas.UserResponse
)
async def login_with_email(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Prisma = Depends(get_db)
):
    user = await db.user.find_unique(where={"email": form_data.username})
    if not user:
        raise AuthExceptions.NotFoundUser

    if not verify_password(form_data.password, user.password):
        raise AuthExceptions.InvalidCredentials

    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user = await db.user.update(
        where={"hash_tag": user.hash_tag},
        data=new_token.dict(exclude_unset=True)
    )
    return user


# @router.post(
#     "/game/signup/guest",
#     tags=[AuthRouterTag.USER],
#     status_code=HTTPStatus.CREATED,
#     response_model=AuthSchemas.GamerUserSchema
# )
# # 게스트 게이머 가입
# async def signup_guest(
#     session: AsyncSession = Depends(unit_of_work)
# ):
#     # 임의의 id 생성
#     device_id = uuid.uuid4()
#     user = await game_uesr_repository.add(
#         session,
#         GameUser(
#             device_id=str(device_id),
#             login_type=LoginType.GUEST,
#         )
#     )
#     return user


# @router.post(
#     "/game/login/guest",
#     tags=[AuthRouterTag.GAMER],
#     response_model=AuthSchemas.GamerUserSchema
# )
# # 게스트 게이머 로그인
# async def login_guest(data: AuthSchemas.GamerUserLoginByGuest, session: AsyncSession = Depends(unit_of_work)):
#     user = await game_uesr_repository.get_one_by(session, device_id=data.device_id)
#     if user == None:
#         raise BadRequest
#     token = AuthSchemas.TokenSchema(
#         access_token=create_token(user.id),
#         refresh_token=create_token(user.id, True)
#     )
#     user.access_token = token.access_token
#     user.refresh_token = token.refresh_token
#     await game_uesr_repository.update(session, user)
#     return user

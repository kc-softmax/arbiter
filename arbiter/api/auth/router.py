import httpx
import arbiter.api.auth.exceptions as AuthExceptions
import arbiter.api.auth.schemas as AuthSchemas
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from http import HTTPStatus
from arbiter.constants import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
from arbiter.database import Database
from arbiter.database.model import User
from arbiter.api.auth.schemas import OAuthRequest
from arbiter.api.auth.dependencies import get_user
from arbiter.api.auth.constants import AuthRouterTag
from arbiter.api.auth.utils import (
    create_token,
    verify_token as verify_token_util,
    get_password_hash,
    verify_password,
)

router = APIRouter(
    prefix="/auth",
)

@router.post(
    "/github/callback",
    tags=[AuthRouterTag.TOKEN],
)
async def github_callback(request: OAuthRequest):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": request.code
            },
            headers={"Accept": "application/json"}
        )

    if response.status_code == 200:
        print(response.json())
        return response.json()
    else:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    
@router.post(
    "/token/refresh",
    tags=[AuthRouterTag.TOKEN],
    response_model=AuthSchemas.TokenSchema
)
async def refresh_token(
    data: AuthSchemas.TokenRefreshRequest,
    db: Database = Depends(Database.get_db)
):
    token_data = verify_token_util(data.refresh_token, True)
    # DB에 저장된 토큰과 같은 토큰인 지 확인
    user = await db.get_data(User, int(token_data.sub))
    if user == None or data.access_token != user.access_token or data.refresh_token != user.refresh_token:
        raise AuthExceptions.InvalidToken

    # 새로운 토큰 발급
    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    await db.update_data(
        user,
        access_token=new_token.access_token,
        refresh_token=new_token.refresh_token
    )
    return new_token


@router.post(
    "/signup/email",
    tags=[AuthRouterTag.USER],
    status_code=HTTPStatus.CREATED,
    response_model=AuthSchemas.UserResponse
)
async def signup_email(
    data: AuthSchemas.UserCreate,
    db: Database = Depends(Database.get_db)
):
    hashed_password = get_password_hash(data.password)
    new_user = await db.create_data(
        User,
        email=data.email,
        password=hashed_password
    )
    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(new_user.id),
        refresh_token=create_token(new_user.id, True)
    )
    new_user = await db.update_data(
        new_user,
        access_token=new_token.access_token,
        refresh_token=new_token.refresh_token
    )
    return new_user


@router.post(
    '/login/email',
    tags=[AuthRouterTag.USER],
    response_model=AuthSchemas.UserResponse
)
async def login_with_email(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Database = Depends(Database.get_db)
):
    users = await db.search_data(User, email=form_data.username)
    if not users:
        raise AuthExceptions.NotFoundUser
    user = users[0]
    if not verify_password(form_data.password, user.password):
        raise AuthExceptions.InvalidCredentials

    new_token = AuthSchemas.TokenSchema(
        access_token=create_token(user.id),
        refresh_token=create_token(user.id, True)
    )
    user = await db.update_data(
        user,
        access_token=new_token.access_token,
        refresh_token=new_token.refresh_token
    )
    return user

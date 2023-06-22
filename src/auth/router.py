from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .dependencies import get_current_user
from .schemas import CreateUserRequest, UserSchema, UserInDB, TokenSchema
from .service import create_user, get_user, authenticate_user
from .utils import create_access_token, create_refresh_token

router = APIRouter()


@router.post("/signup", response_model=UserSchema)
async def signup(data: CreateUserRequest):
    # TODO service의 구현에 따라 달라질 수 있음
    user = get_user(data.email)

    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    # TODO service의 구현에 따라 달라질 수 있음
    user = create_user(data.email, data.password)
    return UserSchema(**user.dict())


@router.post('/login', response_model=TokenSchema)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # TODO service의 구현에 따라 달라질 수 있음
    user = authenticate_user(form_data.username, form_data.password)

    if user is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    return TokenSchema(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email)
    )


# protected test(auth 인증되어야 접근 가능한 api)
@router.get('/users/me', response_model=UserSchema)
async def get_me(user: UserInDB = Depends(get_current_user)):
    return UserSchema(**user.dict())

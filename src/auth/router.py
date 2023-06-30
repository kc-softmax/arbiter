from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from .dependencies import get_current_user
from .schemas import CreateUserRequest, UserSchema, UserInDB, TokenSchema
from .service import check_user_by_email, resister_user_by_email, login_by_email
from .utils import create_access_token, create_refresh_token
from .exceptions import UserAlready, InvalidCredentials, InvalidToken, AuthorizationFailed, NotFoundUser

router = APIRouter(prefix="/auth")


@router.post("/signup",
             response_model=UserSchema,
             operation_id="signup",
             responses={**UserAlready.to_openapi_response()})
async def signup(data: CreateUserRequest):
    user = check_user_by_email(data.email)
    if user is not None:
        raise UserAlready

    user = resister_user_by_email(data.email, data.password)
    return UserSchema(**user.dict())


@router.post('/login', response_model=TokenSchema, responses={**InvalidCredentials.to_openapi_response()})
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = login_by_email(form_data.username, form_data.password)
    if user is None:
        raise InvalidCredentials

    return TokenSchema(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email)
    )


# protected test(auth 인증되어야 접근 가능한 api)
@router.get('/users/me',
            response_model=UserSchema,
            responses={**InvalidToken.to_openapi_response(),
                       **AuthorizationFailed.to_openapi_response(),
                       **NotFoundUser.to_openapi_response()})
async def get_me(user: UserInDB = Depends(get_current_user)):
    return UserSchema(**user.dict())

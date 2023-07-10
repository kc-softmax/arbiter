from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from auth.models import User
from .dependencies import allowed_only_for_admin, get_user_service
from .schemas import CreateUserRequest, UserSchema, TokenSchema
from .service import UserService
from .utils import create_access_token, create_refresh_token
from .exceptions import UserAlready, InvalidCredentials, InvalidToken, AuthorizationFailed, NotFoundUser


router = APIRouter(prefix="/auth")


@router.post("/signup",
             response_model=UserSchema,
             operation_id="signup",
             responses={**UserAlready.to_openapi_response()})
async def signup(data: CreateUserRequest, user_service: UserService = Depends(get_user_service)):
    user = await user_service.check_user_by_email(data.email)
    if user is not None:
        raise UserAlready

    user = await user_service.register_user_by_email(data.email, data.password)
    return UserSchema(**user.dict())


@router.post('/login', response_model=TokenSchema, responses={**InvalidCredentials.to_openapi_response()})
async def login(form_data: OAuth2PasswordRequestForm = Depends(), user_service: UserService = Depends(get_user_service)):
    user = await user_service.login_by_email(form_data.username, form_data.password)
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
async def get_me(user: User = Depends(allowed_only_for_admin)):
    return UserSchema(**user.dict())

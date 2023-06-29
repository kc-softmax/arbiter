from datetime import datetime
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError

from ..config import settings
from .schemas import TokenDataSchema, UserInDB
from .utils import ALGORITHM
from .service import get_user
from .exceptions import InvalidToken, AuthorizationFailed, NotFoundUser


reuseable_oauth = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scheme_name="JWT",
)


async def get_current_user(token: str = Depends(reuseable_oauth)) -> UserInDB:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )

        token_data = TokenDataSchema(
            email=payload.get("sub"),
            exp=payload.get("exp")
        )

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise InvalidToken
    except (JWTError, ValidationError):
        raise AuthorizationFailed

    user = get_user(token_data.email)

    if user is None:
        raise NotFoundUser

    return user

from datetime import datetime
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError

from ..config import settings
from .schemas import TokenDataSchema, UserInDB
from .utils import ALGORITHM
from .service import check_user_by_email
from .exceptions import InvalidToken, AuthorizationFailed, NotFoundUser


async def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl=""))) -> UserInDB:
    try:
        payload = jwt.decode(
            token, settings.JWT_ACCESS_SECRET_KEY, algorithms=[ALGORITHM]
        )

        token_data = TokenDataSchema(
            email=payload.get("sub"),
            exp=payload.get("exp")
        )

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise InvalidToken
    except (JWTError, ValidationError):
        raise AuthorizationFailed

    user = check_user_by_email(token_data.email)
    if user is None:
        raise NotFoundUser

    return user

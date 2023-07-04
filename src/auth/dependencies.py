from datetime import datetime
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from typing import List

from auth.models import User, Role
from ..config import settings
from .schemas import TokenDataSchema
from .utils import ALGORITHM
from .service import check_user_by_email
from .exceptions import InvalidToken, AuthorizationFailed, NotFoundUser, InvalidCredentials


async def get_current_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl=""))) -> User:
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
        raise InvalidCredentials

    user = check_user_by_email(token_data.email)
    if user is None:
        raise NotFoundUser
    return user


class RoleChecker:
    def __init__(self, allowed_roles: List):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise AuthorizationFailed
        return user


allowed_only_for_admin = RoleChecker([Role.OWNER, Role.MAINTAINER])

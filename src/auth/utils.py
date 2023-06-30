from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt
from passlib.context import CryptContext

from ..config import settings
from .constants import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta | None = None):
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode,
                             settings.JWT_ACCESS_SECRET_KEY,
                             algorithm=ALGORITHM)
    return encoded_jwt

# TODO 굳이 2개로 나눌 필요 없으면 하나로 합치기


def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta | None = None):
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode,
                             settings.JWT_REFRESH_SECRET_KEY,
                             algorithm=ALGORITHM)
    return encoded_jwt

from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import ValidationError

from server.config import settings
from server.auth.models import LoginType
from server.auth.constants import TOKEN_GENERATE_ALGORITHM
from server.auth.schemas import TokenDataSchema
from server.auth.exceptions import InvalidToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_token(subject: str, login_type: LoginType,  key: str, expires_delta: timedelta | None = None):
    expire = datetime.utcnow() + expires_delta
    to_encode = {"exp": expire, "sub": subject, "login_type": login_type}
    encoded_jwt = jwt.encode(to_encode,
                             key,
                             algorithm=TOKEN_GENERATE_ALGORITHM.HS256)
    return encoded_jwt


# Temp
# KMT-106과 병합될 때 제거
def verify_token(token: str, is_refresh_token: bool = False):
    token_data = decode_token(token, is_refresh_token)
    if datetime.fromtimestamp(token_data.exp) < datetime.now():
        raise InvalidToken
    return token_data


def decode_token(token: str, is_refresh_token: bool = False):
    key = settings.JWT_REFRESH_SECRET_KEY if is_refresh_token else settings.JWT_ACCESS_SECRET_KEY
    try:
        payload = jwt.decode(
            token, key, algorithms=[
                TOKEN_GENERATE_ALGORITHM.HS256])

        token_data = TokenDataSchema(
            sub=payload.get("sub"),
            exp=payload.get("exp"),
            login_type="guest"
        )
    except (JWTError, ValidationError):
        raise InvalidToken
    return token_data

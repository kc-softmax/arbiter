import hashlib
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import ValidationError
from arbiter.api.config import settings
from arbiter.api.auth.constants import TOKEN_GENERATE_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from arbiter.api.auth.schemas import TokenDataSchema
from arbiter.api.auth.exceptions import InvalidToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_hash_tag(email: str) -> str:
    return hashlib.sha256(email.encode('utf-8')).hexdigest()


def generate_numeric_hash_tag(email: str) -> int:
    hash_object = hashlib.sha256(email.encode('utf-8')).hexdigest()
    numeric_hash = int(hash_object, 16)
    int_hash_tag = numeric_hash % (2**31 - 1)
    return int_hash_tag


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_token(subject: str, is_refresh_token: bool = False):
    key = settings.JWT_REFRESH_SECRET_KEY if is_refresh_token else settings.JWT_ACCESS_SECRET_KEY
    expire_delta = timedelta(
        minutes=REFRESH_TOKEN_EXPIRE_MINUTES if is_refresh_token else ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": datetime.now(
        timezone.utc) + expire_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode,
        key,
        algorithm=TOKEN_GENERATE_ALGORITHM.HS256)
    return encoded_jwt


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
                TOKEN_GENERATE_ALGORITHM.HS256]
        )
        token_data = TokenDataSchema(
            sub=payload.get("sub"),
            exp=payload.get("exp"),
        )
    except (JWTError, ValidationError):
        raise InvalidToken
    return token_data

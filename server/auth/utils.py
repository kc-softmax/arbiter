from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import ValidationError
from ast import literal_eval

from server.config import settings
from server.auth.constants import TOKEN_GENERATE_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from server.auth.schemas import TokenDataSchema
from server.auth.exceptions import InvalidToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_token(subject: str, is_refresh_token: bool = False):
    key = settings.JWT_REFRESH_SECRET_KEY if is_refresh_token else settings.JWT_ACCESS_SECRET_KEY
    expire_delta = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES) if is_refresh_token else timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": datetime.utcnow() + expire_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode,
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


# parse list string and transfrom to list
def list_string_to_list(list_string: str):
    if list_string.isnumeric():
        return [list_string]
    try:
        return literal_eval(list_string)
    except:
        return None

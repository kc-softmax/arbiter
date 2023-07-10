from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

from auth.models import LoginType
from .constants import ALGORITHM

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
                             algorithm=ALGORITHM)
    return encoded_jwt

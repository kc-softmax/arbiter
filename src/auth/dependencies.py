from typing import Union, Any, Annotated
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError

from .schemas import TokenDataSchema, UserInDB
from .utils import ALGORITHM
from .service import get_user
import config

reuseable_oauth = OAuth2PasswordBearer(
    tokenUrl="/login",
    scheme_name="JWT",
)


async def get_current_user(token: str = Depends(reuseable_oauth)) -> UserInDB:
    try:
        payload = jwt.decode(
            token, config.settings.JWT_SECRET_KEY, algorithms=[ALGORITHM]
        )

        token_data = TokenDataSchema(
            email=payload.get("sub"),
            exp=payload.get("exp")
        )

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError) as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user(token_data.email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )

    return user

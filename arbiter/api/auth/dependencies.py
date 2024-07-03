from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from arbiter.api.auth.schemas import UserSchema
from arbiter.api.auth.exceptions import InvalidToken, NotFoundUser
from arbiter.api.auth.utils import verify_token
from arbiter.database import Database, User


async def get_user(
        token: str = Depends(OAuth2PasswordBearer(
            tokenUrl="/auth/login/email")),
        db: Database = Depends(Database.get_db)
) -> User:
    ''' 
    # jwt 토큰을 디코딩하여 현재 auth 정보를 불러온다.
    토큰은 이름(subject), 유효기간(exp), 로그인 방식(login_type) 데이터로 이루어진다.
    그리고 로그인 방식에 따라 각각의 방식으로 요청하여 유저 정보를 가져온다.
    이 때 유저가 없거나 저장된 토큰과 헤더에 담겨 온 토큰이 다를 경우, 예외를 발생시킨다.
    (저장된 토큰과 헤더에 담겨 온 토큰이 다르다는 것은 이미 deprecated된 토큰으로 요청을 보냈다는 뜻)
    '''
    token_data = verify_token(token)
    user = await db.get_data(int(token_data.sub), User)
    if user is None:
        raise NotFoundUser
    # 저장된 액세스토큰과 같은 토큰인지 확인
    if user.access_token != token:
        raise InvalidToken
    return user

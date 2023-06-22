from datetime import datetime
from typing import Optional
from sqlmodel import Column, Field, SQLModel, String, create_engine


sqlite_file_name = "arbiter_test.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# sqllite는 쓰레드 통신을 지원하지 않기 때문에, 아래와 같이 connect_args를 추가해줘야 한다.
# echo ORM log
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = {'extend_existing': True}
    # auto increment
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(sa_column=Column(String(128)), unique=True)
    password: Optional[str] = Field(sa_column=Column(String(128)))
    display_name: Optional[str] = Field(sa_column=Column(String(128)))
    device_id: Optional[str] = Field(sa_column=Column(String(128)))
    verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

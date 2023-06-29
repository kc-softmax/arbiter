from sqlmodel import SQLModel, create_engine


sqlite_file_name = "arbiter_test.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# sqllite는 쓰레드 통신을 지원하지 않기 때문에, 아래와 같이 connect_args를 추가해줘야 한다.
# echo ORM log
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


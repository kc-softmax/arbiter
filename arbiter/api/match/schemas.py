from pydantic import BaseModel


class MatchGameSchema(BaseModel):
    token: str


class MatchGameDataSchema(BaseModel):
    pass
    
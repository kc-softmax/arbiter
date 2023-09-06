import datetime
from bson import ObjectId
from pymongo import MongoClient


my_client = MongoClient("mongodb://localhost:27017/")

mongo_database = my_client['chat_room']

# mongo_database['chat'].drop()
# mongo_database['chat_reaction'].drop()

col_chat = mongo_database['chat']
col_chat_reaction = mongo_database['chat_reaction']


def insert_chat(room_id: int, user_id: int, user_name: str, message: str):
    row = col_chat.insert_one(
        dict(
            room_id=room_id,
            user_id=user_id,
            user_name=user_name,
            message=message,
            created_at=datetime.datetime.now(),
        )
    )
    return row.inserted_id

def get_chat(room_id: int) -> list[dict]:
    cursor = col_chat.find({"room_id":room_id})
    return list(cursor)

def insert_chat_reaction(message_id: int, user_id: int, type: str):
    row = col_chat_reaction.insert_one(
        dict(
            message_id=message_id,
            user_id=user_id,
            type=type
        )
    )
    return row.inserted_id

def chat_reaction_find_one_and_delete(message_id: int, user_id: int, type: str) -> dict:
    return col_chat_reaction.find_one_and_delete({"message_id":message_id, "user_id":user_id, "type":type})

def get_chat_reaction(message_id: int, type: str) -> list[dict]:
    cursor = col_chat_reaction.find({"message_id":message_id, "type":type})
    return list(cursor)

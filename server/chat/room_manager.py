import uuid
from server.auth.models import User
from sqlmodel import select


from server.chat.connection import connection_manager
from server.chat.schemas import ChatData, InviteeData, UserData
from server.chat.models import ChatReaction, ChatRoom, ChatRoomUser, Chat
from server.database import make_async_session, db_manager
from server import mongodb


# is_full
async def is_full(room_id: str) -> bool:
    async with make_async_session() as session:
        chat_room = await db_manager.get_one(session, ChatRoom, room_id=room_id)
        chat_room_users = await db_manager.get_all(session, ChatRoomUser, room_id=room_id)

        if chat_room:
            if len(chat_room_users) < chat_room.max_users:
                return False
        return True


async def is_joined(room_id: str, user_id: int) -> bool:
    async with make_async_session() as session:
        statement = select(ChatRoomUser).where(ChatRoomUser.room_id == room_id).where(
            ChatRoomUser.user_id == user_id).where(ChatRoomUser.is_connected == True)
        result = await session.exec(statement)
        if result.first():
            return True
        return False


async def create_room(room_id: str, max_users: int):
    new_room_id = room_id if room_id else str(uuid.uuid4())
    async with make_async_session() as session:
        await db_manager.create(
            session,
            ChatRoom(
                room_id=new_room_id,
                max_users=max_users
            )
        )


async def get_chat_room(room_id: str) -> ChatRoom | None:
    async with make_async_session() as session:
        return await db_manager.get_one(session, ChatRoom, room_id=room_id)


# TODO: 방 삭제 정책 정리 확실히 되면 다시
async def get_chat_active_rooms() -> list[ChatRoom]:
    async with make_async_session() as session:
        return await db_manager.get_all(session, ChatRoom)


async def get_room_connected_users(room_id: str) -> list[ChatRoomUser]:
    async with make_async_session() as session:
        return await db_manager.get_all(session, ChatRoomUser, room_id=room_id, is_connected=True)

async def get_room_connected_user_list(room_id: str) -> list[UserData]:
    async with make_async_session() as session:
        users = await db_manager.get_all(session, ChatRoomUser, room_id=room_id, is_connected=True)
        user_data = []
        for user in users:
            user_data.append(
                UserData(
                    user_id=user.user_id,
                    user_name="Not Defined"
                )
            )
        return user_data


async def join_room(room_id: str, user_id: int) -> ChatRoomUser:
    async with make_async_session() as session:
        # 이미 들어가 있으면
        if await db_manager.get_one(session, ChatRoomUser, room_id=room_id, user_id=user_id, is_connected=True):
            return None
        return await db_manager.create(session, ChatRoomUser(room_id=room_id, user_id=user_id))


async def leave_room(room_id: str, user_id: int) -> bool:
    async with make_async_session() as session:
        chat_room_user = await db_manager.get_one(session, ChatRoomUser, room_id=room_id, user_id=user_id, is_connected=True)
        if not chat_room_user:
            return False
        await db_manager.update(session, ChatRoomUser(is_connected=False), chat_room_user)
        return True

async def leave_all_rooms(user_id: int) -> bool:
    async with make_async_session() as session:
        cha_room_users = await db_manager.get_all(session, ChatRoomUser, user_id=user_id, is_connected=True)
        for chat_room_user in cha_room_users:
            await db_manager.update(session, ChatRoomUser(is_connected=False), chat_room_user)


async def set_room_notice(room_id: str, notice: str):
    async with make_async_session() as session:
        chat_room = await db_manager.get_one(session, ChatRoom, room_id=room_id)
        if not chat_room:
            return False
        await db_manager.update(session, ChatRoom(notice=notice), chat_room)
        return True


async def get_chat_by_id(message_id: int) -> Chat | None:
    async with make_async_session() as session:
        return await db_manager.get_one(session, Chat, id=message_id)


async def save_message(room_id: str, user_id: int, message: str) -> Chat:
    async with make_async_session() as session:
        return await db_manager.create(session, Chat(room_id=room_id, user_id=user_id, message=message))

def save_message_nosql(room_id: str, user_id: int, user_name: str, message: str):
    mongodb.insert_chat(room_id, user_id, user_name, message)

def set_chat_reaction_nosql(message_id: str, user_id: int, type: str):
    if chat := mongodb.chat_reaction_find_one_and_delete(message_id, user_id, type) is None:
        mongodb.insert_chat_reaction(message_id, user_id, type)
    


# TODO: 우선 return에 맞춘 거라 refactoring 필요
# 저장된 전체 메세지를 가져오게 되니 로직 개선이 필요하다. -> cursor를 사용하면 좋을 꺼 같다.
# 데이터 사용이 명확하면 raw query로 바꿔도 될 듯
async def get_room_messages(room_id: str) -> list[ChatData]:
    async with make_async_session() as session:
        chats = await db_manager.get_all(session, Chat, room_id=room_id)

    chat_data = []
    for chat in chats:
        chat_data.append(
            ChatData(
                room_id=chat.room_id,
                message=chat.message,
                message_id=chat.id,
                user=UserData(user_id=chat.user_id, user_name="test"),
                time=chat.created_at.isoformat(),
                like=len(await get_chat_reaction_by_message_id(chat.id, 'like')),
            )
        )
    return chat_data

def get_room_messages_nosql(room_id: str) -> list[ChatData]:
    chats = mongodb.get_chat(room_id)

    chat_data = []
    for chat in chats:
        message_id = str(chat["_id"])
        chat_data.append(
            ChatData(
                room_id=chat["room_id"],
                message=chat["message"],
                message_id=message_id,
                user=UserData(user_id=chat["user_id"], user_name=chat["user_name"]),
                time=chat["created_at"].isoformat(),
                like=len(get_chat_reaction_by_message_id_nosql(message_id, 'like'))
            )
        )
    return chat_data


async def get_chat_reaction_by_message_id(message_id: int, type: str):
    async with make_async_session() as session:
        return await db_manager.get_all(session, ChatReaction, message_id=message_id, type=type, deprecated=False)

def get_chat_reaction_by_message_id_nosql(message_id: int, type: str) -> list[dict]:
    return mongodb.get_chat_reaction(message_id, type)

async def set_chat_reaction(message_id: int, user_id: int, type: str) -> ChatReaction:
    async with make_async_session() as session:
        chat_reaction = await db_manager.get_one(session, ChatReaction, message_id=message_id, user_id=user_id, type=type, deprecated=False)
        if chat_reaction:
            return await db_manager.update(session, ChatReaction(deprecated=True), chat_reaction)
        else:
            return await db_manager.create(session, ChatReaction(message_id=message_id, user_id=user_id, type=type))

async def get_invitee_users() -> list[InviteeData]:
    async with make_async_session() as session:
        users = await db_manager.get_all(session, User)
        # 최근 만든 아이디
        invitees: list[InviteeData] = []
        for user in users:
            invitees.append(
                InviteeData(
                    user=UserData(
                        user_id=user.id,
                        user_name= user.user_name
                    ),
                    is_online=True if user.id in connection_manager.active_connections else False
                )
            )
        invitees = sorted(invitees, key=lambda x: x.is_online, reverse=True)
        return invitees

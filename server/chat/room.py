import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from fastapi import WebSocket

from server.adapter import ChatAdapter
from server.chat.schemas import (
    ChatSocketRoomJoinMessage, ChatSocketUserJoinMessage, ChatSocketUserLeaveMessage,
    ClientChatMessage, ChatData, LobbyData,
    RoomJoinData, UserData, UserJoinData,
    UserLeaveData, ChatSocketLobbyRefreshMessage
)
from server.chat.router import connection_manager


@dataclass
class MessageSummary:
    total_count: int = 0
    bad_comments_count: int = 0


@dataclass
class ChatRoomData:
    max_users: int = 0
    user_message_summary: dict[str, MessageSummary] = field(default_factory=lambda: defaultdict(MessageSummary))
    created_at: int = 0
    finished_at: int = 0


class ChatRoom:
    max_num = 2

    def __init__(self, room_id: str, adapter: ChatAdapter) -> None:
        self.room_id = room_id
        self.adapter = adapter
        self.message_history: deque[ChatData] = []
        self.current_users: deque[UserData] = []
        self.chat_room_data: ChatRoomData = ChatRoomData(
            created_at=round(datetime.now().timestamp() * 1000))
        self.notice = ""

    def is_available(self) -> bool:
        return len(self.current_users) < self.max_num

    def is_empty(self) -> bool:
        return len(self.current_users) == 0

    def is_duplicate(self, user_id: int) -> bool:
        return user_id in [user.user_id for user in self.current_users]

    def join(self, user_data: UserData):
        self.current_users.append(user_data)
        # 채팅방에 접속한 최대 인원 수
        self.set_max_users()

    def leave(self, user_data: UserData):
        self.current_users.remove(user_data)
        if self.is_empty():
            # 채팅방 종료된 시간
            self.set_finished_time()
            # 데이터 저장
            self.save_chat_room()

    # 소켓 메시지 처리에 대한 비즈니스 로직 부분
    async def handle_chat_message(self, user_data: UserData, client_message: ClientChatMessage) -> ChatData:
        # 채팅 메시지가 없으면 오류
        chat_data = client_message.data
        if (chat_data is None):
            return
        # 각 클라이언트에게 보내줄 메시지 오브젝트를 구성(어댑터 프로세스 적용)
        chat_message_executed_by_adapter = self.adapter.execute(user_data.user_id, chat_data.message)
        chat_socket_message = ChatData(
            message=chat_message_executed_by_adapter["message"],
            user=user_data,
            room_id=self.room_id,
            time=datetime.now().isoformat()
        )
        # 히스토리에 저장
        self.message_history.append(chat_socket_message)
        # index를 message_id로 사용
        chat_socket_message.message_id = len(self.message_history) - 1
        # Chat room에서 각 유저별 채팅 횟수와 비속어 횟수
        # 지금은 메시지를 받을 때마다 매번 기록하지만, 방이 없어질 때 message_history를 순회하면서 한번에 기록도 가능하다.
        self.set_user_message_summary(user_data.user_id, chat_message_executed_by_adapter["is_bad_comments"])
        return chat_socket_message

    # Chat Room 기준의 데이터 로직
    def set_max_users(self):
        current_user_count = len(self.current_users)
        if (current_user_count <= self.chat_room_data.max_users):
            return
        self.chat_room_data.max_users = current_user_count

    def set_user_message_summary(self, user_id: str, is_bad_comments):
        message_summary = self.chat_room_data.user_message_summary[user_id]
        message_summary.total_count += 1
        if is_bad_comments:
            message_summary.bad_comments_count += 1

    def set_finished_time(self):
        if (len(self.current_users) > 0):
            return
        self.chat_room_data.finished_at = round(datetime.now().timestamp() * 1000)

    def save_chat_room(self):
        user_scores = self.calculate_user_score()
        print('데이터', self.chat_room_data)
        print('점수', user_scores)

    # 유저별 점수 계산하기
    def calculate_user_score(self) -> dict:
        user_scores = {}
        for user_id, summary in self.chat_room_data.user_message_summary.items():
            user_scores[user_id] = summary.total_count - summary.bad_comments_count
        return user_scores


class ChatRoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, ChatRoom] = defaultdict(ChatRoom)
        # 접속유저리스트
        # {id: ["room1", "room2"]}
        self.user_in_room: dict[str, list[str]] = defaultdict(list)
        self.is_timer_on: bool = True
        self.delay_time: float = 5
        self.is_begin: bool = False

    # room_id 받아서 처리할 수 있도록 추가
    def create_room(self, receive_room_id: str = '') -> bool:
        room_id = receive_room_id if receive_room_id else str(uuid.uuid4())
        new_room = ChatRoom(room_id, ChatAdapter({}))
        self.rooms[room_id] = new_room
        return True

    def remove_room(self, room_id: str):
        self.rooms.pop(room_id)

    def get_by_room_id(self, room_id: str) -> ChatRoom | None:
        if room_id not in self.rooms:
            return None
        return self.rooms[room_id]

    async def join_room(self, websocket: WebSocket, room_id: str, user_data: UserData) -> bool:
        self.user_in_room[user_data.user_id].append(room_id)
        connection_manager.active_connections[room_id].append(
            {user_data.user_id: websocket}
        )
        self.rooms[room_id].join(user_data)

        # 새로 입장한 유저에게 기존 채팅방 데이터를 보내준다.
        await connection_manager.send_personal_message(
            websocket,
            ChatSocketRoomJoinMessage(
                data=RoomJoinData(
                    room_id=room_id,
                    messages=self.rooms[room_id].message_history,
                    users=self.rooms[room_id].current_users,
                    current_users=len(self.rooms[room_id].current_users),
                    max_users=self.rooms[room_id].max_num,
                    notice=self.rooms[room_id].notice
                )
            )
        )
        # 기존에 있었던 유저들에게 새 유저 입장을 알려준다.
        await connection_manager.send_room_broadcast(
            room_id,
            ChatSocketUserJoinMessage(
                data=UserJoinData(
                    room_id=room_id,
                    user=user_data
                )
            )
        )
        return True

    # TODO: 방 나갔을 때, 접속이 끊겼을때 분리하기
    async def leave_room(self, websocket: WebSocket, room_id: str, user_data: UserData):
        user_id = user_data.user_id
        # 대상이 있으면 그 방만 나가고, 없으면 전부 나간다.
        joined_room_ids = []
        if room_id:
            joined_room_ids.append(room_id)
        else:
            joined_room_ids = self.user_in_room[user_id]

        for room_id in joined_room_ids:
            connection_manager.disconnect(room_id, websocket, user_data.user_id)
            self.rooms[room_id].leave(user_data)
            self.user_in_room[user_id].remove(room_id)
            if self.rooms[room_id].is_empty():
                self.remove_room(room_id)
            else:
                await connection_manager.send_room_broadcast(
                    room_id,
                    ChatSocketUserLeaveMessage(
                        data=UserLeaveData(
                            room_id=room_id,
                            user=user_data
                        )
                    )
                )
        # 접속한 방이 하나도 없으면 접속유저리스트에서 제거
        if len(self.user_in_room[user_id]) == 0:
            del self.user_in_room[user_id]

    # room_manager에 있는게 맞을까?
    async def lobby_refresh_timer(self, delay_time: float):
        if not self.is_begin:
            self.is_begin = True
            self.delay_time = delay_time
            while self.is_timer_on:
                await self.send_lobby_data()
                await asyncio.sleep(self.delay_time)

    async def send_lobby_data(self):
        lobby_data = [
            LobbyData(
                room_id=room.room_id,
                current_users=len(room.current_users),
                max_users=room.max_num
            )
            for room in self.rooms.values()
        ]
        # 내림차순 정렬
        lobby_data = sorted(lobby_data, key=lambda x: x.current_users, reverse=True)

        await connection_manager.send_broadcast(
            ChatSocketLobbyRefreshMessage(
                data=lobby_data
            )
        )

        # 디버깅 용
        for room in self.rooms.values():
            print(room.room_id, room.current_users)

        print(self.user_in_room)

        for rooms in connection_manager.active_connections.values():
            for room in rooms:
                print(room)
        print('---------------------------------------')

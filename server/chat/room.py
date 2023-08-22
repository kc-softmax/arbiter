import uuid
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque

from server.adapter import ChatAdapter
from server.chat.schemas import ClientChatMessage, ChatData


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
        self.current_users: deque[str] = []
        self.chat_room_data: ChatRoomData = ChatRoomData(
            created_at=round(datetime.now().timestamp() * 1000))

    def is_available(self) -> bool:
        return len(self.current_users) < self.max_num

    def is_empty(self) -> bool:
        return len(self.current_users) == 0

    def join(self, user_id: str):
        self.current_users.append(user_id)
        # 채팅방에 접속한 최대 인원 수
        self.set_max_users()

    def leave(self, user_id):
        self.current_users.remove(user_id)
        if self.is_empty():
            # 채팅방 종료된 시간
            self.set_finished_time()
            # 데이터 저장
            self.save_chat_room()

    # 소켓 메시지 처리에 대한 비즈니스 로직 부분
    async def handle_chat_message(self, user_id, client_message: ClientChatMessage) -> ChatData:
        # 채팅 메시지가 없으면 오류
        chat_data = client_message.data
        if (chat_data is None):
            return
        # 각 클라이언트에게 보내줄 메시지 오브젝트를 구성(어댑터 프로세스 적용)
        chat_message_excuted_by_adapter = self.adapter.execute(user_id, chat_data.message)
        chat_socket_message = ChatData(
            message=chat_message_excuted_by_adapter["message"],
            user=user_id,
            time=datetime.now().isoformat()
        )
        # 히스토리에 저장
        self.message_history.append(chat_socket_message)
        # Chat room에서 각 유저별 채팅 횟수와 비속어 횟수
        # 지금은 메시지를 받을 때마다 매번 기록하지만, 방이 없어질 때 message_history를 순회하면서 한번에 기록도 가능하다.
        self.set_user_message_summary(user_id, chat_message_excuted_by_adapter["is_bad_comments"])
        return chat_socket_message

    # Chat Room 기준의 데이터 로직
    def set_max_users(self):
        currnet_user_count = len(self.current_users)
        if (currnet_user_count <= self.chat_room_data.max_users):
            return
        self.chat_room_data.max_users = currnet_user_count

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
        self.rooms: list[ChatRoom] = []

    def find_available_room(self) -> ChatRoom | None:
        available_rooms = [room for room in self.rooms if room.is_available()]
        return available_rooms[0] if available_rooms else None

    # room_id 받아서 처리할 수 있도록 추가
    def create_room(self, receive_room_id: str = '') -> ChatRoom:
        room_id = receive_room_id if receive_room_id else str(uuid.uuid4())
        new_room = ChatRoom(room_id, ChatAdapter({}))
        self.rooms.append(new_room)
        return new_room

    def remove_room(self, room: ChatRoom):
        self.rooms.remove(room)

    def get_by_room_id(self, room_id: str):
        for room in self.rooms:
            if room.room_id == room_id:
                return room
        return None

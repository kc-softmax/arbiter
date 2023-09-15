from typing import Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque

from arbiter.api.live.legacy.room import BaseLiveRoom
from arbiter.api.live.chat.schemas import (
    ClientChatData,
    ChatData
)


@dataclass
class MessageSummary:
    total_count: int = 0
    score: float = 0.0
    bad_comments_count: int = 0


@dataclass
class ChatRoomData:
    user_message_summary: dict[str, MessageSummary] = field(default_factory=lambda: defaultdict(MessageSummary))
    created_at: int = 0
    finished_at: int = 0


class ChatRoom(BaseLiveRoom):
    def __init__(self, room_id: str, max_users: int | None, adapter: Any) -> None:
        super().__init__(room_id, max_users, adapter)
        self.message_history: deque[ChatData] = []
        self.chat_room_data: ChatRoomData = ChatRoomData(
            created_at=round(datetime.now().timestamp() * 1000)
        )

    def leave(self, user_id: str):
        super().leave(user_id)
        if self.is_empty():
            # 채팅방 종료된 시간
            self.set_finished_time()
            # 데이터 저장
            self.save_chat_room()

    # 소켓 메시지 처리에 대한 비즈니스 로직 부분
    async def handle_chat_message(self, user_id, client_chat_data: ClientChatData) -> ChatData:
        # 각 클라이언트에게 보내줄 메시지 오브젝트를 구성(어댑터 프로세스 적용)
        chat_message = await self.adapter.execute(user_id, client_chat_data.message)
        if chat_message['is_bad_comments']:
            chat_message['message'] = len(chat_message['message']) * '*'
        chat_socket_message = ChatData(
            message=chat_message["message"],
            user=user_id,
            time=datetime.now().isoformat()
        )
        # 히스토리에 저장
        self.message_history.append(chat_socket_message)
        # Chat room에서 각 유저별 채팅 횟수와 비속어 횟수
        # 지금은 메시지를 받을 때마다 매번 기록하지만, 방이 없어질 때 message_history를 순회하면서 한번에 기록도 가능하다.
        self.set_user_message_summary(user_id, chat_message["is_bad_comments"], chat_message["score"])
        return chat_socket_message

    # Chat Room 기준의 데이터 로직
    def set_user_message_summary(self, user_id: str, is_bad_comments: bool, score: float):
        message_summary = self.chat_room_data.user_message_summary[user_id]
        message_summary.total_count += 1
        if is_bad_comments:
            message_summary.bad_comments_count += 1
            message_summary.score -= score
        else:
            message_summary.score += score

    def set_finished_time(self):
        if (len(self.current_users) > 0):
            return
        self.chat_room_data.finished_at = round(datetime.now().timestamp() * 1000)

    def save_chat_room(self):
        print('데이터', self.chat_room_data)

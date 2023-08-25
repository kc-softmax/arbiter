from dataclasses import dataclass, field
from enum import IntEnum
import asyncio
import uuid


# ticket
# 매칭을 위한 정보가 있는 매칭 객체
@dataclass
class BaseMatchTicket:
    ticket_id: str
    room_id: str
    mmr: int


@dataclass
class SoloMatchTicket(BaseMatchTicket):
    pass
    # connection: WebSocket


@dataclass
class GroupMatchTicket(BaseMatchTicket):
    pass
    # connections: list[WebSocket]


# match pool
# mmr을 기준으로 그룹화된 매칭 풀(매칭 티켓들이 대기열에 속해있다.)
@dataclass
class MatchPool():
    min_mmr: int
    max_mmr: int
    ticket_pool: list[BaseMatchTicket] = field(default_factory=list)

    def is_included_mmr(self, mmr: int) -> bool:
        return self.min_mmr <= mmr <= self.max_mmr

    def append(self, ticket: BaseMatchTicket):
        self.ticket_pool.append(ticket)

    def remove(self, ticket: BaseMatchTicket):
        self.ticket_pool.remove(ticket)


# 매칭 그룹을 나누는 기준 mmr
class STANDARD_MMR(IntEnum):
    LOW_MIN = 0
    LOW_MAX = 100

    MID_MIN = LOW_MAX + 1
    MID_MAX = 200

    HIGH_MIN = MID_MAX + 1
    HIGH_MAX = 300


# 매칭 로직을 실행하는 매치 메이커
class MatchMaker:
    low_mmr_pool = MatchPool(
        STANDARD_MMR.LOW_MIN,
        STANDARD_MMR.LOW_MAX
    )

    mid_mmr_pool = MatchPool(
        STANDARD_MMR.MID_MIN,
        STANDARD_MMR.MID_MAX
    )
    high_mmr_pool = MatchPool(
        STANDARD_MMR.HIGH_MIN,
        STANDARD_MMR.HIGH_MAX
    )

    # 티켓 생성
    @staticmethod
    def create_solo_match_ticket() -> SoloMatchTicket:
        # mmr 계산 또는 db에서 가져옴.
        # 지금은 임의의 값 넣어줌
        return SoloMatchTicket(ticket_id=str(uuid.uuid4()), mmr=100, room_id=None)

    # 티켓이 어떤 매칭풀에 해당하는지 검사
    # 지금은 그냥 mmr 범위 확인
    @classmethod
    def get_mmr_pool(cls, ticket: BaseMatchTicket) -> MatchPool:
        if cls.low_mmr_pool.is_included_mmr(ticket.mmr):
            return cls.low_mmr_pool
        elif cls.mid_mmr_pool.is_included_mmr(ticket.mmr):
            return cls.mid_mmr_pool
        else:
            return cls.high_mmr_pool

    # 티켓을 매칭풀에 할당
    @classmethod
    def assign_ticket_to_pool(cls, ticket: BaseMatchTicket):
        mmr_pool = cls.get_mmr_pool(ticket)
        mmr_pool.append(ticket)

    # 취소된 티켓 처리
    @classmethod
    def canceld_ticket(cls, ticket: BaseMatchTicket):
        mmr_pool = cls.get_mmr_pool(ticket)
        mmr_pool.remove(ticket)

    # 각각의 매칭풀에서 매칭 조건에 따라 성사되는 매칭 탐색
    # 지금은 그냥 pool에 티켓 2개가 되면 매칭
    # 각각 매칭풀을 병렬로 작업해야하나?
    # 서버가 꺼졌을 때 처리?
    @classmethod
    async def find_match(cls):
        try:
            while True:
                print("matching..")
                await asyncio.sleep(1)
                if len(cls.low_mmr_pool.ticket_pool) >= 2:
                    ticket_1 = cls.low_mmr_pool.ticket_pool.pop()
                    ticket_2 = cls.low_mmr_pool.ticket_pool.pop()

                    matched_room_id = str(uuid.uuid4())
                    ticket_1.room_id = matched_room_id
                    ticket_2.room_id = matched_room_id
        except Exception as e:
            print(e)

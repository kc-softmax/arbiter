import asyncio
import uuid
from dataclasses import dataclass, field
from enum import IntEnum


class MatchType(IntEnum):
    SOLO = 1
    GROUP = 2


# 매칭 그룹을 나누는 기준 mmr
class STANDARD_MMR(IntEnum):
    LOW_MIN = 0
    LOW_MAX = 100

    MID_MIN = LOW_MAX + 1
    MID_MAX = 200

    HIGH_MIN = MID_MAX + 1
    HIGH_MAX = 300


# ticket
# 매칭을 위한 정보가 있는 매칭 객체
@dataclass(kw_only=True)
class BaseMatchTicket():
    ticket_id: str
    mmr: int
    room_id: str | None = None


@dataclass(kw_only=True)
class SoloMatchTicket(BaseMatchTicket):
    user_id: str


@dataclass(kw_only=True)
class GroupMatchTicket(BaseMatchTicket):
    pass


# match pool
# mmr을 기준으로 그룹화된 매칭 풀(매칭 티켓들이 대기열에 속해있다.)
@dataclass
class MatchPool():
    min_mmr: int
    max_mmr: int
    tickets: list[BaseMatchTicket] = field(default_factory=list)

    def is_included_mmr(self, mmr: int) -> bool:
        return self.min_mmr <= mmr <= self.max_mmr

    def get_by_user_id(self, user_id: str):
        filtered = list(filter(lambda ticket: user_id == ticket.user_id, self.tickets))
        return filtered[0] if len(filtered) > 0 else None

    def append(self, ticket: BaseMatchTicket):
        self.tickets.append(ticket)

    def remove(self, ticket: BaseMatchTicket):
        self.tickets.remove(ticket)


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

    def __init__(self) -> None:
        self.matched_tickets: list[BaseMatchTicket] = []
        # For Test
        # self.low_mmr_pool.ticket_pool.append(
        #     SoloMatchTicket(ticket_id='test-ticket-id', user_id='test-user-id', mmr=32)
        # )

    # 티켓 생성
    def create_solo_match_ticket(self) -> SoloMatchTicket:
        # mmr 계산 또는 db에서 가져옴.
        # 지금은 임의의 값 넣어줌
        return SoloMatchTicket(ticket_id=str(uuid.uuid4()), mmr=100)

    # 티켓이 어떤 매칭풀에 해당하는지 검사
    # 지금은 그냥 mmr 범위 확인
    def get_mmr_pool(self, ticket: BaseMatchTicket) -> MatchPool:
        if self.low_mmr_pool.is_included_mmr(ticket.mmr):
            return self.low_mmr_pool
        elif self.mid_mmr_pool.is_included_mmr(ticket.mmr):
            return self.mid_mmr_pool
        else:
            return self.high_mmr_pool

    def assign_ticket_to_pool(self, ticket: BaseMatchTicket):
        mmr_pool = self.get_mmr_pool(ticket)
        mmr_pool.append(ticket)

    def match_tickets(self, tickets: list[BaseMatchTicket]):
        # TODO RoomManager와 연결
        matched_room_id = str(uuid.uuid4())
        for ticket in tickets:
            ticket.room_id = matched_room_id
            self.matched_tickets.append(ticket)

    # 각각의 매칭풀에서 매칭 조건에 따라 성사되는 매칭 탐색
    # 지금은 그냥 pool에 티켓 2개가 되면 매칭
    async def find_match(self, user_id: str, game_type: MatchType):
        # 이미 생성된 티켓이 있는 지 확인
        # TODO 전체 pool에서 검사, 그룹 매칭일 때는 어떻게 해야할까?
        exited_ticket = self.low_mmr_pool.get_by_user_id(user_id)
        if exited_ticket:
            return None
        # create ticket
        created_ticket = SoloMatchTicket(ticket_id=str(uuid.uuid4()), user_id=user_id, mmr=100)
        # insert ticket
        self.assign_ticket_to_pool(created_ticket)
        # config
        timeout = 5
        processing_clock = 1
        elapsed_time = 0
        while (True):
            print("find match")
            await asyncio.sleep(processing_clock)
            # matched
            if created_ticket in self.matched_tickets:
                break
            # timeout
            if elapsed_time > timeout:
                self.cancel_match(created_ticket)
                break
            elapsed_time += 1
        return created_ticket

    def cancel_match(self, ticket: BaseMatchTicket):
        mmr_pool = self.get_mmr_pool(ticket)
        mmr_pool.remove(ticket)

    async def run(self):
        try:
            print('engine start')
            processing_clock = 3
            self.terminated = False
            while not self.terminated:
                # manage pool or find_match request
                await asyncio.sleep(processing_clock)
                # 풀을 관리(매칭)
                if len(self.low_mmr_pool.tickets) >= 2:
                    ticket_1 = self.low_mmr_pool.tickets.pop()
                    ticket_2 = self.low_mmr_pool.tickets.pop()
                    self.match_tickets([ticket_1, ticket_2])
            print('engine close')
        except Exception as e:
            print(e)


match_maker = MatchMaker()

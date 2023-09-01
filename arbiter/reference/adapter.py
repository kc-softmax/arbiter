import asyncio
import timeit
import gymnasium as gym
import torch
import numpy as np

from collections import deque
from contextlib import asynccontextmanager
from transformers import BertForSequenceClassification, BertTokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences


class AsyncAdapter:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    @asynccontextmanager
    async def subscribe(self) -> 'AsyncAdapter':
        try:
            yield self
        finally:
            pass

    async def get(self):
        item = await self._queue.get()
        if item is None:
            raise StopAsyncIteration
        return item

    async def __aiter__(self):
        try:
            while True:
                yield await self.get()
        except Exception:
            pass

    async def execute(self) -> None | dict[str | int, any]:
        raise NotImplementedError()


class GymAdapter(AsyncAdapter):
    def __init__(self, env: gym.Env) -> None:
        super().__init__()
        self.env: gym.Env = env

    def add_user_message(self, agent_id: int | str, action: int) -> list:
        # action은 미리 env에서 정의한 gym.spaces.Discrete의 범위내 값이다.
        self.actions.append((agent_id, action))

    async def execute(self) -> None:
        actions: dict[str | int, int] = {
            agent_id: action
            for agent_id, action in self.actions
        }
        # env의 step에서 action에 대한 타입 체크를 해야한다.
        # multiagent일 경우 step에서 dict으로 처리해야한다.
        obs, rewards, terminateds, truncateds, infos = self.env.step(actions)
        # step의 결과인 update된 state를 queue에 넣는다.
        return obs


class ChatAdapter(AsyncAdapter):
    """
        ChatAdapter for multiplay chatting
    """
    bert_tokenizer: str = 'bert-base-multilingual-cased'
    max_len: int = 128
    dtype: str = "long"
    # pre or post for padding(fill in array the zero)
    truncating: str = "post"
    padding: str = "post"


    def __init__(self, model_path: str) -> None:
        super().__init__()
        # model에 사용되는 속성 값이 복잡하여 정의된 속성 값만 사용한다.
        self.model: BertForSequenceClassification = BertForSequenceClassification.from_pretrained(model_path)
        self.tokenizer: BertTokenizer = BertTokenizer.from_pretrained(self.bert_tokenizer, do_lower_case=False)
        # 평가모드로 변경
        self.model.eval()
        if torch.cuda.is_available():    
            self.device = torch.device("cuda")
            print('There are %d GPU(s) available.' % torch.cuda.device_count())
            print('We will use the GPU:', torch.cuda.get_device_name(0))
        else:
            self.device = torch.device("cpu")
            print('No GPU available, using the CPU instead.')
    
    def convert_sentences(self, sentences: list[str]) -> tuple[torch.Tensor, torch.Tensor]:
        # BERT의 토크나이저로 문장을 토큰으로 분리
        tokenized_texts = [
            self.tokenizer.tokenize(sentence)
            for sentence in sentences
        ]
        # 토큰을 숫자 인덱스로 변환
        token_ids = [
            self.tokenizer.convert_tokens_to_ids(tokenized_text)
            for tokenized_text in tokenized_texts
        ]
        
        # 문장을 MAX_LEN 길이에 맞게 자르고, 모자란 부분을 패딩 0으로 채움
        padding_sequences: np.ndarray = pad_sequences(
            token_ids,
            maxlen=self.max_len,
            dtype=self.dtype,
            truncating=self.truncating,
            padding=self.padding
        )

        # 어텐션 마스크 초기화
        attention_masks: list[list[float]] = []

        # 어텐션 마스크를 패딩이 아니면 1, 패딩이면 0으로 설정
        # 패딩 부분은 BERT 모델에서 어텐션을 수행하지 않아 속도 향상
        for sequences in padding_sequences:
            seq_mask: list[float] = [
                float(sequence > 0)
                for sequence in sequences
            ]
            attention_masks.append(seq_mask)

        # 데이터를 파이토치의 텐서로 변환
        tensored_sequences: torch.Tensor = torch.tensor(padding_sequences)
        tensored_masks: torch.Tensor = torch.tensor(attention_masks)
        return tensored_sequences, tensored_masks
    
    def apply_bert_model(self, sentences: list[str]) -> torch.Tensor:
        tensored_sequences, tensored_masks = self.convert_sentences(sentences)

        # 데이터를 GPU or CPU에 넣음
        cpu_sequences_sequences: torch.Tensor = tensored_sequences.to(self.device)
        cpu_masks: torch.Tensor = tensored_masks.to(self.device)
            
        # 그래디언트 계산 안함
        with torch.no_grad():     
            # Forward 수행
            outputs = self.model(
                cpu_sequences_sequences, 
                token_type_ids=None, 
                attention_mask=cpu_masks
            )
            logits: torch.Tensor = outputs[0]
            # CPU로 데이터 이동
            logits = logits.detach().cpu().numpy()
        return logits

    async def execute(self, user_id: int | str, message: str) -> dict[str, any]:
        # 처음에는 단순하게 '비속어'라는 단어의 유무에 따라 유저의 메시지를 분류한다.
        filtered_message: np.ndarray = self.apply_bert_model([message])
        # 가장 큰 인덱스를 리턴시킨다 0 or 1 둘 중 하나
        # 0은 비속어, 1은 일반어
        idx = np.argmax(filtered_message)
        if idx == 1: is_bad_comments = False
        else: is_bad_comments = True

        user_message: dict[str | int, str] = {
            'user_id': user_id,
            'message': message,
            'score': float(filtered_message[0][idx]),
            'is_bad_comments': is_bad_comments,
        }
        # 처리된 결과를 브로드캐스팅 할 메시지 큐에 넣는다.
        return user_message

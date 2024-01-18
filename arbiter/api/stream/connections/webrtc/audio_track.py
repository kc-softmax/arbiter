import asyncio
import time
import fractions

from contextlib import contextmanager, asynccontextmanager, AbstractContextManager
from aiortc.mediastreams import AudioStreamTrack
from av import AudioFrame
from av.frame import Frame

AUDIO_PTIME = 0.020  # 20ms audio packetization


class MediaStreamError(Exception):
    pass


class AudioPacketStreamTrack(AudioStreamTrack):
    kind = "audio"

    _start: float
    _timestamp: int

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__()

    async def recv(self) -> Frame:
        # client-server에서 client로 전송되는 데이터
        """
        Receive the next :class:`~av.audio.frame.AudioFrame`.

        The base implementation just reads silence, subclass
        :class:`AudioStreamTrack` to provide a useful implementation.
        """
        if self.readyState != "live":
            raise MediaStreamError

        sample_rate = 8000
        samples = int(AUDIO_PTIME * sample_rate)

        if hasattr(self, "_timestamp"):
            self._timestamp += samples
            wait = self._start + (self._timestamp / sample_rate) - time.time()
            await asyncio.sleep(wait)
        else:
            self._start = time.time()
            self._timestamp = 0

        frame = AudioFrame(format="s16", layout="mono", samples=samples)
        for p in frame.planes:
            p.update(bytes(p.buffer_size))
        frame.pts = self._timestamp
        frame.sample_rate = sample_rate
        frame.time_base = fractions.Fraction(1, sample_rate)
        return frame

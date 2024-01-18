# import numpy
# import fractions
# import math
# import cv2
# import random
# import asyncio

# from aiortc import VideoStreamTrack
# from av import VideoFrame


# AUDIO_PTIME = 0.020  # 20ms audio packetization
# VIDEO_CLOCK_RATE = 90000
# VIDEO_PTIME = 1 / 30  # 30fps
# VIDEO_TIME_BASE = fractions.Fraction(1, VIDEO_CLOCK_RATE)


# class FlagVideoStreamTrack(VideoStreamTrack):
#     """
#     A video track that returns an animated flag.
#     """

#     def __init__(self):
#         super().__init__()  # don't forget this!
#         self.counter = 0
#         height, width = 480, 640

#         # generate flag
#         data_bgr = numpy.hstack(
#             [
#                 self._create_rectangle(
#                     width=213, height=480, color=(random.randint(0, 256), random.randint(0, 256), random.randint(0, 256))
#                 ),  # blue
#                 self._create_rectangle(
#                     width=214, height=480, color=(random.randint(0, 256), random.randint(0, 256), random.randint(0, 256))
#                 ),  # white
#                 self._create_rectangle(width=213, height=480, color=(random.randint(0, 256), random.randint(0, 256), random.randint(0, 256))),  # red
#             ]
#         )

#         # shrink and center it
#         M = numpy.float32([[0.5, 0, width / 4], [0, 0.5, height / 4]])
#         data_bgr = cv2.warpAffine(data_bgr, M, (width, height))

#         # compute animation
#         omega = 2 * math.pi / height
#         id_x = numpy.tile(numpy.array(range(width), dtype=numpy.float32), (height, 1))
#         id_y = numpy.tile(
#             numpy.array(range(height), dtype=numpy.float32), (width, 1)
#         ).transpose()

#         self.frames = []
#         for k in range(30):
#             phase = 2 * k * math.pi / 30
#             map_x = id_x + 10 * numpy.cos(omega * id_x + phase)
#             map_y = id_y + 10 * numpy.sin(omega * id_x + phase)
#             self.frames.append(
#                 VideoFrame.from_ndarray(
#                     cv2.remap(data_bgr, map_x, map_y, cv2.INTER_LINEAR), format="bgr24"
#                 )
#             )

#     async def recv(self):
#         # client-server에서 client로 전송되는 데이터
#         pts, time_base = await self.next_timestamp()

#         frame = self.frames[self.counter % 30]
#         frame.pts = pts
#         frame.time_base = time_base
#         self.counter += 1
#         # await asyncio.sleep(2)
#         return frame

#     def _create_rectangle(self, width, height, color):
#         data_bgr = numpy.zeros((height, width, 3), numpy.uint8)
#         data_bgr[:, :] = color
#         return data_bgr

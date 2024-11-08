# import aiohttp
# import logging
# import pytest
# import json
# import asyncio


# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)


# base_url = "{protocol}://localhost:8080"

# """
# importlib error in :  Invalid response type: <class 'bytes'>,
# allowed types: (<class 'pydantic.main.BaseModel'>, <class 'list'>,
# <class 'int'>, <class 'str'>, <class 'float'>, <class 'bool'>,
# <class 'datetime.datetime'>) 리턴 타입 참고
# """

# # send는 str 타입으로 보낸다
# @pytest.mark.asyncio
# async def test_stream_ping_pong():
#     session = aiohttp.ClientSession()
#     url = f'{base_url.format(protocol="ws")}/stream/test_service'
#     async with session.ws_connect(url) as conn:
#         # enter chat room
#         await conn.send_json({
#             "channel": "simple_ping_pong",
#             "target": "1"
#         })
#         recv = await conn.receive_str()
#         assert type(recv) == str
#         assert recv == 'OK'

#         await asyncio.sleep(1)

#         # send message
#         await conn.send_json({
#             "channel": "simple_ping_pong",
#             "target": "1",
#             "data": "ping"
#         })
#         res = await conn.receive_str(timeout=1)
#         logger.info(res)
#     await session.close()


# @pytest.mark.asyncio
# async def test_stream_type_of_text():
#     session = aiohttp.ClientSession()
#     url = f'{base_url.format(protocol="ws")}/stream/test_service'
#     async with session.ws_connect(url) as conn:
#         # enter chat room
#         await conn.send_str(json.dumps({
#             "channel": "type_of_text",
#             "target": "1"
#         }))
#         recv = await conn.receive_str()
#         assert type(recv) == str
#         assert recv == 'OK'

#         await asyncio.sleep(1)

#         # send message
#         await conn.send_str(json.dumps({
#             "channel": "type_of_text",
#             "target": "1",
#             "data": "ping"
#         }))
#         res = await conn.receive_str(timeout=1)
#         logger.info(res)
#     await session.close()

import pytest
import httpx
import aiohttp
import logging
import json


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


base_url = "{protocol}://localhost:8080"


def test_http_number_of_param():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/return_constant")
        assert response.status_code == 200, "What happend"
        data = response.json()
        assert data == "HI"


def test_http_wrong_url():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/return_")
        assert response.status_code == 404, "What happend"


def test_http_type_of_param():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/return_annotation", data=json.dumps({'data': '1'}))
        data = response.json()
        assert type(data) == str, "Not matched type"


@pytest.mark.asyncio
async def test_stream_chat():
    session = aiohttp.ClientSession()
    url = f'{base_url.format(protocol="ws")}/stream/test_service'
    async with session.ws_connect(url) as conn:
        # enter chat room
        await conn.send_json({
            "channel": "village",
            "target": "1"
        })
        recv = await conn.receive_str()
        assert type(recv) == str
        assert recv == 'OK'

        # send message
        await conn.send_json({
            "channel": "village",
            "target": "1",
            "data": "hello world"
        })
    await session.close()

import httpx
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


base_url = "{protocol}://localhost:8080"


def test_exception_connection_timeout():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_exception/connection_timeout", timeout=10)
        assert response.json()['detail'], logger.error(response.text)


def test_exception_connection_exceed():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_exception/connection_exceed", timeout=10)
        assert response.json()['detail'], logger.error(response.text)


def test_exception_task_timeout():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_exception/task_timeout", timeout=10)
        assert response.json()['detail'], logger.error(response.text)

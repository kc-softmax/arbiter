import httpx
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


base_url = "{protocol}://localhost:8080"

"""
importlib error in :  Invalid response type: <class 'bytes'>,
allowed types: (<class 'pydantic.main.BaseModel'>, <class 'list'>,
<class 'int'>, <class 'str'>, <class 'float'>, <class 'bool'>,
<class 'datetime.datetime'>) 리턴 타입 참고
"""

def test_http_task_chain():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/task_chain")
        assert response.status_code == 200, logger.error(response.text)

def test_http_async_task_chain():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/async_task_chain")
        assert response.status_code == 200, logger.error(response.text)

def test_http_num_of_param_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/num_of_param", json={"first": '1', "second": 1})
        assert response.status_code == 200, logger.error(response.text)

def test_http_num_of_param_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/num_of_param", json={"first": '1', "second": 1})
        assert response.status_code == 200, logger.error(response.text)


def test_http_type_of_param_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/type_of_param", json={"first": True, "second": 2}, timeout=10)
        assert response.status_code == 200, logger.error(response.text)


def test_http_bad_type_of_param_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/type_of_param", json={"first": -1, "second": 2}, timeout=10)
        assert response.status_code == 400, logger.error(response.text)


def test_http_empty_type_of_param_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/type_of_param", timeout=10)
        assert response.status_code == 400, logger.error(response.text)


def test_http_wrong_type_of_param_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/wrong_type_of_param", json={"first": True, "second": 2}, timeout=10)
        assert response.status_code == 400, logger.error(response.text)


def test_http_wrong_url_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/return_")
        assert response.status_code == 404, logger.error(response.text)


def test_http_return_value_type():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/num_of_param", json={"first": 1, "second": 2}, timeout=10)
        data = response.json()
        assert type(data) == dict, logger.error(response.text)
        assert data == {
            'first': 1,
            'second': 'second',
            'third': True
        }

def test_http_return_no_body():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/return_nobody", timeout=10)
        data = response.json()
        assert data == None, logger.error(response.text)


# get은 보류
# def test_http_get_query_param():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.get("/test_service/get_query_param?first=1&second=second", timeout=10)
#         data = response.json()
#         logger.info(data)

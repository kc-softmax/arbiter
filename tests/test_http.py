import httpx
import json
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

def test_http_default_param():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        x = 10
        response = arbiter.get("/test_service/test_default_parameter", params={"x": x})
        data = response.json()
        assert type(data) != dict, logger.error(response.text)
        assert data == x + 5
        
def test_http_test_default_param_with_value():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        x = 10
        y = 20
        response = arbiter.get("/test_service/test_default_parameter_with_value", params={"x": x, "y": y})
        data = response.json()
        assert type(data) != dict, logger.error(response.text)
        assert data == x + y

def test_http_integer_parameter():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        x = 10
        y = 20
        response = arbiter.get("/test_service/integer_parameter", params={"x": x, "y": y})
        data = response.json()
        assert type(data) != dict, logger.error(response.text)
        assert data == x + y

def test_http_task_chain():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        first = 10
        second = 20
        response = arbiter.post("/test_service/task_chain", json={"first": first, "second": second})
        data = response.json()
        assert type(data) == dict, logger.error(response.text)
        assert data == {
            'first': first + second,
            'second': second - first,
        }

def test_http_task_chain_using_dict():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        first = 10
        second = 20
        response = arbiter.post("/test_service/task_chain_using_dict", json={"first": first, "second": second})
        data = response.json()
        assert type(data) == dict, logger.error(response.text)
        assert data == {
            'first': first + second,
            'second': second - first,
        }

def test_http_stream_task_chain():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        payload = {"content": "HIHIHI", "length": 5}
        start = 0
        with arbiter.stream("POST", "/test_service/stream_task_chain", json=payload) as response:
            assert response.status_code == 200, logger.error(response.text)
            for chunk in response.iter_text():
                if receive := chunk.strip():
                    receive_data = json.loads(receive)
                    assert receive_data == {
                        'content': f"{payload['content']}-{start}"
                        }
                    start += 1
            assert start == payload["length"], logger.error(response.text)

def test_simple_http_stream_task_chain():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        payload = {"content": "HIHIHI", "length": 5}
        start = 0
        with arbiter.stream("POST", "/test_service/simple_http_stream_task", json=payload) as response:
            assert response.status_code == 200, logger.error(response.text)
            for chunk in response.iter_text():
                if receive := chunk.strip():
                    receive_data = json.loads(receive)
                    assert receive_data == {
                        'content': f"{payload['content']}-{start}"
                        }
                    start += 1

def test_http_num_of_param_status_code():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        response = arbiter.post("/test_service/num_of_param", json={"first": '1', "second": 1})
        assert response.status_code == 200, logger.error(response.text)

def test_http_return_constant():
    with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
        first = 1
        second = 1
        response = arbiter.post("/test_service/return_constant", json={"first": first, "second": second})
        data = response.text
        assert data == str(first + second + 5), logger.error(response.text)


# def test_http_type_of_param_status_code():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.post("/test_service/type_of_param", json={"first": True, "second": 2}, timeout=10)
#         assert response.status_code == 200, logger.error(response.text)


# def test_http_bad_type_of_param_status_code():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.post("/test_service/type_of_param", json={"first": -1, "second": 2}, timeout=10)
#         assert response.status_code == 400, logger.error(response.text)


# def test_http_empty_type_of_param_status_code():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.post("/test_service/type_of_param", timeout=10)
#         assert response.status_code == 400, logger.error(response.text)


# def test_http_wrong_type_of_param_status_code():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.post("/test_service/wrong_type_of_param", json={"first": True, "second": 2}, timeout=10)
#         assert response.status_code == 400, logger.error(response.text)


# def test_http_wrong_url_status_code():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.post("/test_service/return_")
#         assert response.status_code == 404, logger.error(response.text)


# def test_http_return_value_type():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.post("/test_service/num_of_param", json={"first": 1, "second": 2}, timeout=10)
#         data = response.json()
#         assert type(data) == dict, logger.error(response.text)
#         assert data == {
#             'first': 1,
#             'second': 'second',
#             'third': True
#         }

# def test_http_return_no_body():
#     with httpx.Client(base_url=base_url.format(protocol="http")) as arbiter:
#         response = arbiter.post("/test_service/return_nobody", timeout=10)
#         data = response.json()
#         assert data == None, logger.error(response.text)
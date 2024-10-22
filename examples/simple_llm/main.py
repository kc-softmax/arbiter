import httpx
from arbiter import Arbiter, ArbiterRunner, ArbiterNode
from arbiter.configs import NatsBrokerConfig, ArbiterNodeConfig, ArbiterConfig
from fastapi import FastAPI

import uvicorn

topics = [
    "Employee Benefits",
    "Work-Life Balance", 
    "Remote Work Policies", 
    "Employee Training",
    "Workplace Safety"]

topic_maps = {
    "Employee Benefits": "employee_benefits",
    "Work-Life Balance": "work_life_balance",
    "Remote Work Policies": "remote_work_policies",
    "Employee Training": "employee_training",
    "Workplace Safety": "workplace_safety"
}

ollama_server_1  = "http://192.168.210.194:8082/api"
ollama_server_2  = "http://192.168.210.194:8081/api"

server_maps = {
    "Employee Benefits": ollama_server_1,
    "Work-Life Balance": ollama_server_1,
    "Remote Work Policies": ollama_server_2,
    "Employee Training": ollama_server_2,
    "Workplace Safety": ollama_server_2
}


# ############################################################################################################
app = ArbiterNode(
    arbiter_config=ArbiterConfig(
        broker_config=NatsBrokerConfig(
            port=45817,
            user="local",
            password="Ohe47FvRyPvH6gnEELJtX1ZFe7O70GEb"
        )),
    node_config=ArbiterNodeConfig(system_timeout=5),    
    gateway=uvicorn.Config(app=FastAPI(), host="0.0.0.0", port=8080)
)

def send_llm_request(topic: str, content: str) -> str:
    url = server_maps.get(topic)
    with httpx.Client(base_url=url) as client:
        response = client.post("/generate", json={
            "model": "llama3.2",
            "stream": False,
            "prompt": content,
        })
        data = response.json()
        return data["response"]

@app.http_task()
async def get_llm_request_from_client(
    topic: str,
    content: str,
    arbiter: Arbiter
) -> str:
    target_queue = topic_maps.get(topic)
    if not target_queue:
        return "Invalid topic"
    response = await arbiter.async_task(
        target=target_queue,
        topic=topic, 
        content=content)
    return response

@app.async_task(queue='employee_benefits')
async def send_llm_requset_to_employee_benefits(topic: str, content: str) -> str:
    return send_llm_request(topic, content)
 
@app.async_task(queue='work_life_balance')
async def send_llm_requset_to_work_life_balance(topic: str, content: str) -> str:
    return send_llm_request(topic, content)

@app.async_task(queue='remote_work_policies')
async def send_llm_requset_to_remote_work_policies(topic: str, content: str) -> str:
    return send_llm_request(topic, content)

@app.async_task(queue='employee_training')
async def send_llm_requset_to_employee_training(topic: str, content: str) -> str:
    return send_llm_request(topic, content)

@app.async_task(queue='workplace_safety')
async def send_llm_requset_to_workplace_safety(topic: str, content: str) -> str:
    return send_llm_request(topic, content)


if __name__ == '__main__':
    ArbiterRunner.run(
        app,
        reload=False,
        # repl=True
    )

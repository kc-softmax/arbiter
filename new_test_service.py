from dummy import Arbiter
from dummy import ArbiterRunner


app = Arbiter()

@app.http_task(method="HttpMethod.POST", queue="num_of_params", num_of_tasks=1)
async def num_of_params(a: int, b: str):
    pass


@app.stream_task(
    connection="StreamMethod.WEBSOCKET",
    communication_type="StreamCommunicationType.BROADCAST")
async def vilage():
    pass


if __name__ == '__main__':
    ArbiterRunner.run(app, host="0.0.0.0", port=8000)

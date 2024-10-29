from arbiter import ArbiterRunner, ArbiterNode
from arbiter.configs import NatsBrokerConfig, ArbiterNodeConfig, ArbiterConfig
from tinydb import TinyDB, Query
db = TinyDB('db.json')

# ############################################################################################################
app = ArbiterNode(
    arbiter_config=ArbiterConfig(
        broker_config=NatsBrokerConfig(
            # port=45817,
            # user="local",
            # password="Ohe47FvRyPvH6gnEELJtX1ZFe7O70GEb"
        )),
    node_config=ArbiterNodeConfig(system_timeout=5),    
    gateway=None
)


@app.async_task()
async def store_request(
    topic: str, 
    content: str,
    request: dict,
    answer: str=None
):
    db.insert({'topic': topic, 'content': content, 'answer': answer})

@app.http_task()
async def get_history():
    return db.all()

if __name__ == '__main__':
    ArbiterRunner.run(
        app,
        reload=True,
    )
    

"""
 Simple temporary script to test the arbiter nats
"""
import asyncio
from arbiter.configs import NatsBrokerConfig, ArbiterConfig
from arbiter.task import ArbiterAsyncTask, ArbiterSubscribeTask, ArbiterPeriodicTask
from arbiter import Arbiter

@ArbiterPeriodicTask(interval=1)
async def simple_periodic_task(x: list[int] = []):
    for i in x:
        print("periodic task: ", i)

@ArbiterSubscribeTask()
async def simple_subscribe_task(x: int):
    print("subscribe task: ", x)
    pass

@ArbiterAsyncTask(queue='test_service_return_task')
async def simple_async_task(x: int):
    return {"result": "success + " + str(x)}
        
@ArbiterAsyncTask(queue='test_service_return_stream')
async def simple_async_stream(x: int):
    for i in range(5):
        yield {"result": "success_stream + " + str(x + i)}

async def main():
    arbiter = Arbiter(ArbiterConfig(broker_config=NatsBrokerConfig()))
    
    await arbiter.connect()
    print("async task: ", await arbiter.async_task('get_llm_request_from_client', 5, 4))
    task = asyncio.create_task(simple_async_task(arbiter=arbiter))
    stream = asyncio.create_task(simple_async_stream(arbiter=arbiter))
    periodic = asyncio.create_task(simple_periodic_task(arbiter=arbiter))
    subscribe = asyncio.create_task(simple_subscribe_task(arbiter=arbiter))
    try:
        await asyncio.sleep(0.5)
        await arbiter.async_broadcast('simple_subscribe_task', 5)
        print("async task: ", await arbiter.async_task('get_llm_request_from_client', 5, 4))
        results = await arbiter.async_task('test_service_return_task', 4)
        print("async task: ", results)
        async for results in arbiter.async_stream('test_service_return_stream', 4):
            print("async stream: ", results)
                
        await arbiter.async_broadcast('simple_subscribe_task', 35)
        await arbiter.emit_message('simple_periodic_task', 6)
        await arbiter.emit_message('simple_periodic_task', 5)
        await arbiter.emit_message('simple_periodic_task', 4)
        await arbiter.emit_message('simple_periodic_task', 3)
        
        await asyncio.sleep(2)
        
    except Exception as e:
        print(e)
        
    task and task.cancel()
    stream and stream.cancel()
    periodic and periodic.cancel()
    subscribe and subscribe.cancel()
    
    try:
        await periodic
    except asyncio.CancelledError:
        pass

    try:
        await subscribe
    except asyncio.CancelledError:
        pass

    try:
        await stream
    except asyncio.CancelledError:
        pass

    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # wait task is done
    await arbiter.disconnect()    

if __name__ == '__main__':
    
    asyncio.run(main())
import argparse
import gevent
import signal
import asyncio

from gevent import monkey; monkey.patch_all()
from gunicorn.app.base import BaseApplication
from gunicorn.arbiter import Arbiter as scheduler
from arbiter.api import get_app, ArbiterApiApp


class Application(BaseApplication):

    def __init__(self, app: ArbiterApiApp, options: dict = None):
        self.options = options or {}
        self.application = app
        super().__init__()
        self.scheduler = scheduler(self)

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    async def check_system(self, node_id: str, service_id: str):
        await asyncio.sleep(10)
        while True:
            await asyncio.sleep(5)
            self.scheduler.signal(signal.SIGTERM, None)
            break


    def manage_scheduler(self, node_id: str, service_id: str):
        loop = asyncio.new_event_loop()
        _ = loop.create_task(self.check_system(node_id, service_id))
        loop.run_forever()

    def run(self, node_id: str, service_id: str):
        try:
            gevent.joinall([
                gevent.spawn(self.manage_scheduler, *[node_id, service_id]),
                gevent.spawn(self.scheduler.run)
            ])
            # await loop.create_task(self.start_service(loop))
        except Exception as err:
            print(err)

    def load(self):
        return self.application


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='ArbiterMainApp',
        description='What the program does',
        epilog='Text at the bottom of help'
    )

    parser.add_argument('-n', '--node-id')
    parser.add_argument('-b', '--bind')
    parser.add_argument('-w', '--worker')      # option that takes a value
    parser.add_argument('-k', '--worker-class')
    parser.add_argument('-l', '--log-level')

    args = parser.parse_args()

    options = {
        'bind': args.bind,
        'workers': args.worker,
        'worker_class': args.worker_class,
        'log_level': args.log_level,
    }
    import uuid
    node_id = uuid.uuid4().hex
    Application(get_app(), options).run(node_id, node_id)

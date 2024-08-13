import argparse
import asyncio
import concurrent.futures

from gunicorn.app.base import BaseApplication
from arbiter.api import get_app
from gunicorn.sock import BaseSocket


class ArbiterBaseApp(BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='ArbiterMainApp',
        description='What the program does',
        epilog='Text at the bottom of help'
    )

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
    ArbiterBaseApp(get_app(), options).run()
from arbiter import ArbiterRunner, ArbiterApp
from arbiter.api import get_app
from arbiter.api.app import ArbiterUvicornWorker
from tests.test_worker import TestWorker

# app = ArbiterApp()
# # app.add_worker(TestWorker)

# if __name__ == '__main__':
#     ArbiterRunner.run(app)

ArbiterUvicornWorker.run(get_app())

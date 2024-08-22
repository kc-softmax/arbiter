from arbiter import ArbiterRunner, ArbiterApp
from tests.test_worker import TestWorker

app = ArbiterApp()
app.add_worker(TestWorker)

if __name__ == '__main__':
    ArbiterRunner.run(app)
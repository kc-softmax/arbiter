from arbiter import ArbiterRunner, ArbiterApp
from tests.test_service import TestService

app = ArbiterApp()
app.add_service(TestService)

if __name__ == '__main__':
    ArbiterRunner.run(app)

from arbiter import ArbiterRunner, ArbiterApp
from tests.test_service import TestService, TestException

app = ArbiterApp()
app.add_service(TestService)
app.add_service(TestException)

if __name__ == '__main__':
    ArbiterRunner.run(app)

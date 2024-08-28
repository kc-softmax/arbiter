from arbiter.runner import ArbiterRunner
from arbiter.api import ArbiterApiApp

app = ArbiterApiApp("test")

ArbiterRunner.run(app)
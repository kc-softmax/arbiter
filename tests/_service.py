from arbiter._task.task import ArbiterTask
from arbiter._service.service import ArbiterService


service = ArbiterService("service", "node")
task1 = ArbiterTask("task1", "node", "service")
task2 = ArbiterTask("task2", "node", "service")
service.add_task(task1)
service.add_task(task2)

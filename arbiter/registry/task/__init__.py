import time
from collections import defaultdict
from arbiter.data.models import ArbiterTaskModel
from arbiter.enums import ModelState


class TaskRegistry:
    
    def __init__(self):
        # get, set할 때 어떤 노드인지 알 수 있는 방법
        self.tasks: dict[str, list[ArbiterTaskModel]] = defaultdict(list)
    
    def register_task(self, node_id: str, task: ArbiterTaskModel) -> None:
        self.tasks[node_id].append(task)
    
    def register_tasks(self, node_id: str, tasks: list[ArbiterTaskModel]) -> None:
        self.tasks[node_id].extend(tasks)
    
    def unregister_task(self, node_id: str, task_id: str) -> None:
        self.tasks[node_id] = [task for task in self.tasks[node_id] if task.get_id() != task_id]
    
    def unregister_tasks(self, node_id: str) -> None:
        self.tasks.pop(node_id, None)

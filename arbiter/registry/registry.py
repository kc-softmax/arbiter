import time
from arbiter.data.models import (
    ArbiterNode,
    ArbiterTaskNode,
)
from arbiter.enums import NodeState
from arbiter.registry.node_catalog import NodeCatalog
from arbiter.registry.task_catalog import TaskCatalog


class Registry:
    def __init__(self):
        # get, set할 때 어떤 노드인지 알 수 있는 방법
        self.arbiter_nodes: NodeCatalog = NodeCatalog()
        self.task_nodes: TaskCatalog = TaskCatalog()
        self.node_health: dict[str, int] = {}
        self.http_reload = False # TEMP

    @property
    def local_node(self) -> ArbiterNode:
        return self.arbiter_nodes.local_node

    @property
    def local_task_node(self) -> list[ArbiterTaskNode]:
        return self.task_nodes.local_node


    @property
    def all_active_http_tasks(self, gateway: str = "") -> list[ArbiterTaskNode]:
        active_http_tasks = []
        for nodes in self.task_nodes.nodes.values():
            for node in nodes:
                if node.state == NodeState.ACTIVE and node.http and node.gateway == gateway:
                    active_http_tasks.append(node)
        for node in self.task_nodes.local_node:
            if node.state == NodeState.ACTIVE and node.http and node.gateway == gateway:
                active_http_tasks.append(node)
        return active_http_tasks

    @local_node.setter
    def local_node(self, value):
        self.arbiter_nodes.local_node = value

    @local_task_node.setter
    def local_task_node(self, value):
        self.task_nodes.local_node = value

    @property
    def raw_node_info(self) -> dict[
        str, ArbiterNode | ArbiterTaskNode
    ]:
        node_info: dict[
            str, ArbiterNode | ArbiterTaskNode
        ] = {
            'node': self.local_node,
            'task': self.local_task_node,
        }
        return node_info        

    def update_health_signal(self, node_id: str) -> None:
        self.node_health[node_id] = time.time()
    
    def check_node_healths(self, timeout: int) -> bool:
        current_time = time.time()
        failed_node_ids = []
        for node_id, last_health_time in self.node_health.items():
            if current_time - last_health_time > timeout:
                failed_node_ids.append(node_id)
        
        for node_id in failed_node_ids:
            self.clear_node(node_id)
        
        return failed_node_ids
    
    def failed_health_signal(self, node_id: str) -> None:
        if node_id in self.node_health:
            # set health to -100 for immediate clear from health check
            self.node_health[node_id] = -100

    def create_local_node(self, node: ArbiterNode) -> None:
        self.arbiter_nodes.create_local_node(node)

    def create_local_task_node(self, node: ArbiterTaskNode) -> None:
        self.task_nodes.create_local_node(node)
        if node.http:
            self.http_reload = True

    def update_local_task_node(self, node_info: dict[str, str]) -> None:
        updated_node = self.task_nodes.update_local_node(node_info)
        if updated_node.http:
            self.http_reload = True        

    def register_node(self, node: ArbiterNode) -> None:
        self.arbiter_nodes.add(node)
        self.update_health_signal(node.get_id())
        
    def register_task_node(self, node_id: str, nodes: list[ArbiterTaskNode]) -> None:
        self.task_nodes.add(node_id, nodes)
        self.check_http_reload(nodes)
        
    def get_node(self, node_id: str) -> ArbiterNode:
        return self.arbiter_nodes.get(node_id)

    def get_task_node(self, node_id: str) -> list[ArbiterTaskNode]:
        return self.task_nodes.get(node_id)

    def unregister_node(self, node_id: str) -> None:
        self.arbiter_nodes.remove(node_id)

    def unregister_task_node(self, node_id: str) -> None:
        # find http task in node and set http_reload to True
        if node_id in self.task_nodes.nodes:
            self.check_http_reload(self.task_nodes.nodes[node_id])
        self.task_nodes.remove(node_id)

    def check_http_reload(self, nodes: list[ArbiterTaskNode]) -> None:
        for node in nodes:
            if node.http:
                self.http_reload = True

    def clear_node(self, node_id: str) -> None:
        # external health check에서 확인하여 제거하는 것이 정확 할 것 같다
        self.unregister_node(node_id)
        self.unregister_task_node(node_id)
        self.node_health.pop(node_id, None)

    def clear(self):
        self.local_node = None
        self.local_task_node = []
        self.node_health.clear()
        self.arbiter_nodes.clear()
        self.task_nodes.clear()

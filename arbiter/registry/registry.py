from arbiter.data.models import (
    ArbiterNode,
    ArbiterServiceNode,
    ArbiterTaskNode,
)
from arbiter.registry.node_catalog import NodeCatalog
from arbiter.registry.service_catalog import ServiceCatalog
from arbiter.registry.task_catalog import TaskCatalog


class Registry:
    def __init__(self):
        # get, set할 때 어떤 노드인지 알 수 있는 방법
        self.arbiter_nodes: NodeCatalog = NodeCatalog()
        self.service_nodes: ServiceCatalog = ServiceCatalog()
        self.task_nodes: TaskCatalog = TaskCatalog()
        self.node_health: dict[str, int] = {}

    @property
    def local_node(self) -> ArbiterNode:
        return self.arbiter_nodes.local_node

    # @property
    # def local_service_node(self) -> ArbiterServiceNode:
    #     return self.service_nodes.local_node

    @property
    def local_task_node(self) -> list[ArbiterTaskNode]:
        return self.task_nodes.local_node

    @local_node.setter
    def local_node(self, value):
        self.arbiter_nodes.local_node = value

    @local_task_node.setter
    def local_task_node(self, value):
        self.task_nodes.local_node = value

    @property
    def raw_node_info(self) -> dict[
        str, ArbiterNode | ArbiterServiceNode | ArbiterTaskNode
    ]:
        node_info: dict[
            str, ArbiterNode | ArbiterServiceNode | ArbiterTaskNode
        ] = {
            'node': self.local_node,
            # 'service': self.local_service_node,
            'task': self.local_task_node,
        }
        return node_info

    def get_health_signal(self, node_id: str, received_time: float) -> None:
        self.node_health[node_id] = received_time

    def failed_health_signal(self, node_id: str) -> None:
        self.node_health.pop(node_id, None)

    def create_local_node(self, node: ArbiterNode) -> None:
        self.arbiter_nodes.create_local_node(node)

    def create_local_serivce_node(self, node: ArbiterServiceNode) -> None:
        self.service_nodes.create_local_node(node)

    def create_local_task_node(self, node: ArbiterTaskNode) -> None:
        self.task_nodes.create_local_node(node)

    def register_node(self, node: ArbiterNode) -> None:
        self.arbiter_nodes.add(node)

    def register_service_node(self, node_id: str, node: list[ArbiterServiceNode]) -> None:
        self.service_nodes.add(node_id, node)

    def register_task_node(self, node_id: str, node: list[ArbiterTaskNode]) -> None:
        self.task_nodes.add(node_id, node)

    def get_node(self, node_id: str) -> ArbiterNode:
        return self.arbiter_nodes.get(node_id)

    def get_service_node(self, node_id: str) -> list[ArbiterServiceNode]:
        return self.service_nodes.get(node_id)

    def get_task_node(self, node_id: str) -> list[ArbiterTaskNode]:
        return self.task_nodes.get(node_id)

    def unregister_node(self, node_id: str) -> None:
        self.arbiter_nodes.remove(node_id)

    def unregister_service_node(self, node_id: str) -> None:
        self.service_nodes.remove(node_id)

    def unregister_task_node(self, node_id: str) -> None:
        self.task_nodes.remove(node_id)

    def clear(self):
        self.local_node = None
        self.local_task_node = []
        self.node_health.clear()
        self.arbiter_nodes.clear()
        self.task_nodes.clear()

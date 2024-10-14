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

    def register_node(self, node: ArbiterNode) -> None:
        self.arbiter_nodes.set_node(node.node_id, node)
        self._register_service(node.node_id, node.service_nodes)

    def _register_service(self, node_id: str, node: list[ArbiterServiceNode]) -> None:
        self.service_nodes.set_node(node_id, node)
        for service_node in node:
            self._register_task(node_id, service_node.task_nodes)

    def _register_task(self, node_id: str, node: list[ArbiterTaskNode]) -> None:
        self.task_nodes.set_node(node_id, node)

    def get_node(self, node_id: str) -> ArbiterNode:
        return self.arbiter_nodes.get_node(node_id)

    def _get_service(self, node_id: str) -> list[ArbiterServiceNode]:
        return self.service_nodes.get_node(node_id)

    def _get_task(self, node_id: str) -> list[ArbiterTaskNode]:
        return self.task_nodes.get_node(node_id)

    def disconnect(self, node_id: str):
        self.arbiter_nodes.remove_node(node_id)
        self.service_nodes.remove_node(node_id)
        self.task_nodes.remove_node(node_id)

    def clear(self):
        self.arbiter_nodes.clear()
        self.service_nodes.clear()
        self.task_nodes.clear()

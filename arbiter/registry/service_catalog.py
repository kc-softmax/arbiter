from arbiter.data.models import ArbiterServiceNode
from collections import defaultdict


class ServiceCatalog:
    def __init__(self) -> None:
        self.nodes: dict[str, list[ArbiterServiceNode]] = defaultdict(list)
        self.local_node: list[ArbiterServiceNode] = []

    def create_local_node(self, node: ArbiterServiceNode) -> None:
        self.local_node.append(node)

    # def add(self, node_id: str, node: ArbiterServiceNode) -> None:
    #     if self.nodes.get(node_id):
    #         before_updated_node = [filter(lambda x: x.node_id == node_id, self.nodes[node_id])]
    #         if before_updated_node:
    #             idx = self.nodes[node_id].index(before_updated_node)
    #             self.nodes[node_id][idx] = node
    #         else:
    #             self.nodes[node_id].append(node)
    #     else:
    #         self.nodes[node_id].append(node)

    def add(self, node_id: str, node: list[ArbiterServiceNode]) -> None:
        self.nodes[node_id] = node

    def get(self, node_id: str) -> list[ArbiterServiceNode]:
        return self.nodes.get(node_id)

    def remove(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

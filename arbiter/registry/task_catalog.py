from arbiter.data.models import ArbiterTaskNode
from collections import defaultdict


class TaskCatalog:
    def __init__(self) -> None:
        self.nodes: dict[str, list[ArbiterTaskNode]] = defaultdict(list)

    def set_node(self, node_id: str, node: ArbiterTaskNode) -> None:
        if self.nodes.get(node_id):
            before_updated_node = [filter(lambda x: x.node_id == node_id, self.nodes[node_id])]
            if before_updated_node:
                idx = self.nodes[node_id].index(before_updated_node)
                self.nodes[node_id][idx] = node
            else:
                self.nodes[node_id].append(node)
        else:
            self.nodes[node_id].append(node)

    def get_node(self, node_id: str) -> list[ArbiterTaskNode]:
        return self.nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        if self.nodes.get(node_id):
            self.nodes.pop(node_id)

    def clear(self):
        self.nodes.clear()

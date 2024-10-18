from arbiter.data.models import ArbiterTaskNode
from collections import defaultdict


class TaskCatalog:
    def __init__(self) -> None:
        self.nodes: dict[str, list[ArbiterTaskNode]] = defaultdict(list)
        self.local_node: list[ArbiterTaskNode] = []

    def create_local_node(self, node: ArbiterTaskNode) -> None:
        # local task node에서 뭐가 업데이트 되었는지 알아야한다
        before_updated_node = list(filter(lambda x: x.queue == node.queue, self.local_node))
        if before_updated_node:
            idx = self.local_node.index(before_updated_node[0])
            self.local_node[idx] = node
        else:
            self.local_node.append(node)

    # def add(self, node_id: str, node: ArbiterTaskNode) -> None:
    #     if self.nodes.get(node_id):
    #         before_updated_node = [filter(lambda x: x.node_id == node_id, self.nodes[node_id])]
    #         if before_updated_node:
    #             idx = self.nodes[node_id].index(before_updated_node)
    #             self.nodes[node_id][idx] = node
    #         else:
    #             self.nodes[node_id].append(node)
    #     else:
    #         self.nodes[node_id].append(node)

    def add(self, node_id: str, node: list[ArbiterTaskNode]) -> None:
        self.nodes[node_id] = node

    def get(self, node_id: str) -> list[ArbiterTaskNode]:
        return self.nodes.get(node_id)

    def remove(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

    def clear(self) -> None:
        self.nodes.clear()

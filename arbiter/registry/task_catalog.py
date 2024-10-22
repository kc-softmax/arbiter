from arbiter.data.models import ArbiterTaskNode
from collections import defaultdict


class TaskCatalog:
    def __init__(self) -> None:
        self.nodes: dict[str, list[ArbiterTaskNode]] = defaultdict(list)
        self.local_node: list[ArbiterTaskNode] = []

    def create_local_node(self, node: ArbiterTaskNode) -> None:
        # node 객체가 들올 때에는 local node에 추가만한다
        self.local_node.append(node)

    def update_local_node(self, node_info: dict[str, int]) -> ArbiterTaskNode:
        before_updated_node = list(filter(lambda x: x.node_id == node_info['node_id'], self.local_node))
        if before_updated_node:
            idx = self.local_node.index(before_updated_node[0])
            self.local_node[idx].state = node_info['state']
            return self.local_node[idx]
        else:
            # 등록되기 전에 업데이트가 될 수 있다? 발생하면 로직 다시 확인해보기
            raise Exception("node not found")

    def add(self, node_id: str, node: list[ArbiterTaskNode]) -> None:
        self.nodes[node_id] = node

    def get(self, node_id: str) -> list[ArbiterTaskNode]:
        return self.nodes.get(node_id)

    def remove(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

    def clear(self) -> None:
        self.nodes.clear()

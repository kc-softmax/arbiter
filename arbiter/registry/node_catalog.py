from arbiter.data.models import ArbiterNode
from arbiter.enums import NodeState


class NodeCatalog:
    def __init__(self, name: str) -> None:
        self.nodes: dict[str, ArbiterNode] = {}
        self.local_node: ArbiterNode = ArbiterNode(
            name=name,
            state=NodeState.ACTIVE
        )

    def add(self, node: ArbiterNode) -> None:
        node_id = node.get_id()
        self.nodes[node_id] = node

    def get(self, node_id: str) -> ArbiterNode:
        return self.nodes.get(node_id)

    def remove(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

    def clear(self) -> None:
        self.nodes.clear()

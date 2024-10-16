from arbiter.data.models import ArbiterNode


class NodeCatalog:
    def __init__(self) -> None:
        self.nodes: dict[str, ArbiterNode] = {}
        self.local_node: ArbiterNode = None

    def create_local_node(self, node: ArbiterNode) -> None:
        self.local_node = node

    def add(self, node: ArbiterNode) -> None:
        node_id = node.get_id()
        self.nodes[node_id] = node

    def get(self, node_id: str) -> ArbiterNode:
        return self.nodes.get(node_id)

    def remove(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

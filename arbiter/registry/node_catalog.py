from arbiter.data.models import ArbiterNode


class NodeCatalog:
    def __init__(self) -> None:
        self.nodes: dict[str, ArbiterNode] = {}

    def set_node(self, node_id: str, node: ArbiterNode) -> None:
        self.nodes[node_id] = node

    def get_node(self, node_id: str) -> ArbiterNode | None:
        return self.nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        if self.nodes.get(node_id):
            self.nodes.pop(node_id)

    def clear(self):
        self.nodes.clear()

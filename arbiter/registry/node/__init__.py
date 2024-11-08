import time
from arbiter.data.models import ArbiterNodeModel
from arbiter.enums import ModelState

class NodeRegistry:
    
    def __init__(self):
        self.nodes: dict[str, ArbiterNodeModel] = {}
        self._heartbeat: dict[str, int] = {}
    
    def heartbeat(self, node_id: str) -> None:
        self._heartbeat[node_id] = time.time()
    
    def health_check(self, timeout: int) -> list[str]:
        current_time = time.time()
        removed_node_ids = [
            node_id for node_id, last_health_time in self._heartbeat.items()
            if current_time - last_health_time > timeout
        ]
        for node_id in removed_node_ids:
            self.unregister_node(node_id)
        return removed_node_ids

    def disconnect_node(self, node_id: str) -> None:
        self._heartbeat[node_id] = -1000

    def get_node(self, node_id: str) -> ArbiterNodeModel:
        return self.nodes.get(node_id)

    def register_node(self, node: ArbiterNodeModel) -> None:
        self.nodes[node.get_id()] = node                

    def unregister_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        self._heartbeat.pop(node_id, None)
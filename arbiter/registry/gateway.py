import uvicorn

registry = {}

def register_gateway(name: str, gateway: uvicorn.Config):
    """FastAPI 인스턴스를 레지스트리에 등록"""
    registry[name] = gateway

def get_gateway(name: str) -> uvicorn.Config:
    """레지스트리에서 FastAPI 인스턴스를 조회"""
    return registry.get(name)
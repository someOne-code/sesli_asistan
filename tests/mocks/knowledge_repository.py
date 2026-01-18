from typing import Dict, Optional, Any
from app.core.interfaces.knowledge_repository import IKnowledgeRepository

class FakeKnowledgeRepository(IKnowledgeRepository):
    """
    In-memory implementation for testing.
    Fully compliant with IKnowledgeRepository interface.
    """
    def __init__(self):
        self._knowledge_store: Dict[str, Dict[str, str]] = {}
        self._tenant_store: Dict[str, Dict[str, Any]] = {}

    def add_knowledge(self, tenant_id: str, topic_key: str, content: str):
        if tenant_id not in self._knowledge_store:
            self._knowledge_store[tenant_id] = {}
        self._knowledge_store[tenant_id][topic_key] = content
        
    def add_tenant_info(self, tenant_id: str, info: Dict[str, Any]):
        self._tenant_store[tenant_id] = info
        
    def get(self, tenant_id: str, topic_key: str, locale: str = "tr") -> Optional[str]:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        return self._knowledge_store.get(tenant_id, {}).get(topic_key)

    def exists(self, tenant_id: str, topic_key: str) -> bool:
        if not tenant_id:
            raise ValueError("tenant_id is required")
        return topic_key in self._knowledge_store.get(tenant_id, {})

    def get_tenant_info(self, tenant_id: str) -> Dict[str, Any]:
        return self._tenant_store.get(tenant_id, {"ad": "Default Test Tenant"})

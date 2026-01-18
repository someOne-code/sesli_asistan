from enum import Enum
from typing import Set, NamedTuple

class Capability(Enum):
    """
    Defines the vocabulary of restrictable capabilities in the system.
    This enum does NOT enforce permissions, it only names them.
    """
    SEARCH_PRODUCTS = "search_products"
    AI_ASSISTANT = "ai_assistant"
    TENANT_MANAGEMENT = "tenant_management"
    SYSTEM_ADMIN = "system_admin"

class TenantCapabilities(NamedTuple):
    """
    Carries the set of enabled capabilities for a tenant.
    """
    enabled: Set[Capability]

    @staticmethod
    def none() -> 'TenantCapabilities':
        return TenantCapabilities(set())

    @staticmethod
    def all() -> 'TenantCapabilities':
        return TenantCapabilities(set(Capability))

    def has(self, capability: Capability) -> bool:
        return capability in self.enabled

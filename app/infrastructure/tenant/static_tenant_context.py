# -*- coding: utf-8 -*-
"""
Static Tenant Context - FOR TESTING ONLY
=========================================
This implementation provides a fixed tenant for testing.

⚠️ WARNING: This is NOT for production use.
Production must use request-scoped implementations.
"""

from app.core.interfaces.tenant_context import ITenantContext
from app.core.exceptions.tenant import TenantNotResolvedError


class StaticTenantContext(ITenantContext):
    """
    Static tenant context for testing.
    
    This provides a fixed tenant_id, useful for:
    - Unit tests
    - Integration tests
    - Local development
    
    ⚠️ DO NOT use in production - tenant must be request-scoped.
    """
    
    def __init__(self, tenant_id: str | None):
        """
        Initialize with a fixed tenant.
        
        Args:
            tenant_id: Tenant to use, or None to simulate missing tenant
        """
        self._tenant_id = tenant_id
    
    def get_current_tenant(self) -> str:
        """
        Get the static tenant.
        
        Returns:
            tenant_id string
            
        Raises:
            TenantNotResolvedError: If tenant_id is None
        """
        if not self._tenant_id or not self._tenant_id.strip():
            raise TenantNotResolvedError(
                "Tenant could not be resolved (StaticTenantContext has no tenant)"
            )
        return self._tenant_id
        
    def get_tenant_config(self, tenant_id: str) -> dict:
        """
        Mock configuration for testing purposes.
        Returns meaningful config for 'berber_ahmet'.
        """
        if tenant_id == "berber_ahmet":
            return {
                "tenant_id": "berber_ahmet",
                "ad": "Berber Ahmet Efendi",
                "sektor": "berber",
                "ozellikler": ["randevu", "fiyat_sorgulama", "sac_modeli_önerisi"],
                "maintenance_mode": False
            }
        
        # Default fallback
        return {
            "tenant_id": tenant_id,
            "ad": f"{tenant_id} İşletmesi",
            "sektor": "genel",
            "maintenance_mode": False
        }

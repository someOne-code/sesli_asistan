# -*- coding: utf-8 -*-
"""
Tenant Context Interface - Request-Scoped Tenant Resolution
============================================================
This interface defines HOW tenant is resolved for the current request.

CRITICAL RULES:
1. Tenant MUST be request-scoped (not config-based)
2. Missing tenant = HARD FAILURE (TenantNotResolvedError)
3. Core depends on THIS interface, not implementation
4. Config-based tenant is FOR TESTS ONLY

This enables:
- Multi-tenant SaaS
- Request isolation
- No cross-tenant data leaks
"""

from abc import ABC, abstractmethod
from app.core.capabilities import TenantCapabilities

class ITenantContext(ABC):
    """
    Interface for resolving tenant in the current request context.
    
    Implementations:
    - StaticTenantContext (tests only)
    - SessionTenantContext (from session_id)
    - JWTTenantContext (from JWT token)
    - HeaderTenantContext (from API key header)
    """
    
    @abstractmethod
    def get_current_tenant(self) -> str:
        """
        Get tenant_id for the current request.
        
        CRITICAL: This MUST raise TenantNotResolvedError if tenant cannot be determined.
        NO silent defaults. NO fallbacks.
        
        Returns:
            tenant_id string
            
        Raises:
            TenantNotResolvedError: If tenant cannot be resolved
            
        Example:
            >>> context.get_current_tenant()
            "chinook_music"
            
            >>> context.get_current_tenant()  # No tenant in request
            TenantNotResolvedError: "Tenant could not be resolved from request"
        """
        pass

    def get_capabilities(self) -> TenantCapabilities:
        """
        Get the capabilities enabled for the current tenant.
        
        DEFAULT: Returns ALL capabilities (open system).
        Future implementations should override this to return plan-specific capabilities.
        
        Returns:
            TenantCapabilities object
        """
        return TenantCapabilities.all()

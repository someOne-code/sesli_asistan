# -*- coding: utf-8 -*-
"""
Tenant Context Provider
========================
Provides tenant_id for multi-tenant operations.

DEPLOYMENT STRATEGY:
- Development: Hardcoded default tenant
- Staging: From config/environment
- Production: From session/JWT token
"""

from typing import Optional


class TenantContextProvider:
    """
    Provides tenant context for the current request/session.
    
    This is a simple implementation for single-tenant deployment.
    For true multi-tenancy, this would extract tenant_id from:
    - Session data
    - JWT token
    - API key
    - Subdomain
    """
    
    def __init__(self, default_tenant: str = "chinook_music"):
        """
        Initialize with default tenant.
        
        Args:
            default_tenant: Default tenant ID for single-tenant mode
        """
        self.default_tenant = default_tenant
    
    def get_tenant_id(self, session_id: Optional[str] = None) -> str:
        """
        Get tenant ID for current context.
        
        Args:
            session_id: Optional session identifier
            
        Returns:
            Tenant ID string
            
        Note:
            In production, this would:
            1. Parse session_id to extract tenant
            2. Validate tenant exists
            3. Check permissions
            
            For now, returns default tenant.
        """
        # TODO Sprint-2: Extract from session/JWT
        # For now, return default tenant (single-tenant mode)
        return self.default_tenant
    
    def validate_tenant(self, tenant_id: str) -> bool:
        """
        Validate that tenant exists and is active.
        
        Args:
            tenant_id: Tenant to validate
            
        Returns:
            True if valid, False otherwise
            
        Note:
            In production, this would query tenant registry.
        """
        # TODO Sprint-2: Query tenant registry
        # For now, accept default tenant only
        return tenant_id == self.default_tenant

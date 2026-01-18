# -*- coding: utf-8 -*-
"""
Tenant Exceptions
=================
Exceptions related to tenant resolution and isolation.
"""


class TenantNotResolvedError(Exception):
    """
    Raised when tenant cannot be determined from request context.
    
    This is a CRITICAL error - system MUST NOT proceed without tenant.
    
    Example:
        raise TenantNotResolvedError("Tenant could not be resolved from session")
    """
    pass


class TenantIsolationViolationError(Exception):
    """
    Raised when cross-tenant data access is attempted.
    
    This should NEVER happen in production if architecture is correct.
    """
    pass

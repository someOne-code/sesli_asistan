# -*- coding: utf-8 -*-
"""
Tenant Context Enforcement Tests - RED PHASE
=============================================
These tests enforce that tenant is ALWAYS required.

CRITICAL: These tests MUST FAIL until proper implementation exists.

Test Philosophy:
1. System MUST crash without tenant (no silent defaults)
2. Cross-tenant data leaks MUST be impossible
3. Config-based tenant is FOR TESTS ONLY
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.core.exceptions.tenant import TenantNotResolvedError


class TestTenantContextEnforcement:
    """
    Tests that enforce tenant is ALWAYS resolved from request context.
    
    These tests MUST FAIL until we implement proper tenant context.
    """
    
    def test_service_fails_when_tenant_is_missing(self):
        """
        CRITICAL: Service MUST crash if tenant cannot be resolved.
        
        This test will FAIL until we enforce tenant context.
        """
        from app.core.services.assistant_service import AssistantService
        from app.core.interfaces.tenant_context import ITenantContext
        
        # Create a tenant context that CANNOT resolve tenant
        class FailingTenantContext(ITenantContext):
            def get_current_tenant(self) -> str:
                raise TenantNotResolvedError("No tenant in request")
        
        # Setup service with failing tenant context
        mock_db = MagicMock()
        mock_ai = AsyncMock()
        
        service = AssistantService(
            db_repo=mock_db,
            ai_service=mock_ai,
            tenant_context=FailingTenantContext()
        )
        
        # Act & Assert: MUST raise TenantNotResolvedError
        with pytest.raises(TenantNotResolvedError):
            # This will fail because we're not handling the exception yet
            import asyncio
            asyncio.run(service.process_user_input("Vizyonunuz nedir?", "session_123"))
    
    def test_repository_rejects_none_tenant(self):
        """
        CRITICAL: Repository MUST reject None/empty tenant_id.
        
        This prevents accidental cross-tenant data leaks.
        """
        from app.infrastructure.database.knowledge_repository import SqlKnowledgeRepository
        
        repo = SqlKnowledgeRepository("hedef.db")
        
        # Test 1: None tenant
        with pytest.raises(ValueError, match="tenant_id is required"):
            repo.get(None, "vizyon")
        
        # Test 2: Empty string tenant
        with pytest.raises(ValueError, match="tenant_id is required"):
            repo.get("", "vizyon")
        
        # Test 3: Whitespace tenant
        with pytest.raises(ValueError, match="tenant_id is required"):
            repo.get("   ", "vizyon")
    
    def test_cross_tenant_isolation(self):
        """
        CRITICAL: Different tenants MUST get different data.
        
        This verifies tenant isolation at DB level.
        """
        from app.infrastructure.database.knowledge_repository import SqlKnowledgeRepository
        
        repo = SqlKnowledgeRepository("hedef.db")
        
        # Fetch vision for chinook_music
        vision_chinook = repo.get("chinook_music", "vizyon")
        
        # Fetch vision for non-existent tenant
        vision_other = repo.get("hotel_istanbul", "vizyon")
        
        # Assert: Different tenants get different data (or None)
        assert vision_chinook is not None, "chinook_music should have vision"
        assert vision_other is None, "hotel_istanbul should NOT have data"
        
        # Critical: Same topic, different tenants = different results
        assert vision_chinook != vision_other


class TestTenantContextInterface:
    """
    Tests for ITenantContext interface contract.
    """
    
    def test_interface_requires_get_current_tenant(self):
        """
        Verify ITenantContext interface has correct method.
        """
        from app.core.interfaces.tenant_context import ITenantContext
        import inspect
        
        # Check method exists
        assert hasattr(ITenantContext, 'get_current_tenant')
        
        # Check it's abstract
        sig = inspect.signature(ITenantContext.get_current_tenant)
        assert 'self' in sig.parameters
    
    def test_static_tenant_context_for_tests(self):
        """
        Verify we have a test-only implementation.
        
        This will FAIL until we create StaticTenantContext.
        """
        from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
        from app.core.exceptions.tenant import TenantNotResolvedError
        
        # Test 1: Valid tenant
        context = StaticTenantContext("test_tenant")
        assert context.get_current_tenant() == "test_tenant"
        
        # Test 2: No tenant = CRASH
        context_no_tenant = StaticTenantContext(None)
        with pytest.raises(TenantNotResolvedError):
            context_no_tenant.get_current_tenant()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

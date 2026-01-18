# -*- coding: utf-8 -*-
"""
Knowledge Resolver - Semantic Routing Layer
============================================
This component sits between IntentClassifier and AssistantService.

RESPONSIBILITY:
- Convert raw intent metadata into concrete knowledge requests
- Resolve scope + topic using providers
- Decide which repository to query

DOES NOT:
- Classify intent (that's IntentClassifier's job)
- Access database directly (that's Repository's job)
- Generate responses (that's AI Service's job)

Clean Architecture:
- Depends on interfaces (IScopeProvider, ITopicProvider)
- Returns structured KnowledgeRequest
- No coupling to infrastructure
"""

from dataclasses import dataclass
from typing import Optional
from app.core.interfaces.signal_providers import IScopeSignalProvider, ITopicSignalProvider


@dataclass
class KnowledgeRequest:
    """
    Structured request for knowledge retrieval.
    
    This is the OUTPUT of KnowledgeResolver.
    AssistantService uses this to query the correct repository.
    
    Attributes:
        scope: Query scope (company, product, general)
        target: Data source (knowledge, catalog, external)
        topic_key: Canonical topic for DB lookup
        confidence: Resolution confidence (0.0-1.0)
    """
    scope: str
    target: str
    topic_key: str
    confidence: float = 1.0


class KnowledgeResolver:
    """
    Resolves INFORMATIONAL intents into concrete knowledge requests.
    
    This is the "smart router" that:
    1. Takes IntentResult with minimal metadata
    2. Uses providers to determine scope/topic
    3. Returns structured KnowledgeRequest
    
    Example Flow:
        User: "Vizyonunuz nedir?"
        IntentClassifier: IntentResult(type=INFORMATIONAL, meta_data={"raw_text": "..."})
        KnowledgeResolver: KnowledgeRequest(scope="company", target="knowledge", topic_key="vizyon")
        AssistantService: knowledge_repo.get("vizyon")
    """
    
    def __init__(
        self,
        scope_provider: IScopeSignalProvider,
        topic_provider: ITopicSignalProvider
    ):
        """
        Initialize resolver with providers.
        
        Args:
            scope_provider: Provides scope detection signals
            topic_provider: Maps user text to topic keys
        """
        self.scope_provider = scope_provider
        self.topic_provider = topic_provider
    
    def resolve(self, user_text: str, intent_metadata: dict) -> KnowledgeRequest:
        """
        Resolve INFORMATIONAL intent into knowledge request.
        
        Args:
            user_text: Normalized user input
            intent_metadata: Metadata from IntentClassifier
            
        Returns:
            Structured knowledge request
            
        Logic:
        1. Check scope (company vs product vs general)
        2. Extract topic key
        3. Determine target repository
        """
        # Step 1: Scope detection
        company_signals = self.scope_provider.get_company_signals()
        product_signals = self.scope_provider.get_product_signals()
        
        has_company_signal = any(sig in user_text for sig in company_signals)
        has_product_signal = any(sig in user_text for sig in product_signals)
        
        # Scope priority: company > product > general
        if has_company_signal and not has_product_signal:
            scope = "company"
            target = "knowledge"
        elif has_product_signal:
            scope = "product"
            target = "catalog"
        else:
            scope = "general"
            target = "knowledge"
        
        # Step 2: Topic extraction
        topic_key = self.topic_provider.resolve_topic(user_text)
        
        # Step 3: Build request
        return KnowledgeRequest(
            scope=scope,
            target=target,
            topic_key=topic_key,
            confidence=1.0 if has_company_signal else 0.7
        )

"""
AssistantService - The Coordinator (Clean Pipeline Architecture).
PHASE 3.5: Service Integration.
Delegates logic to specialized components, does NOT contain business rules itself.
"""


import time
import re
import logging
from typing import Dict, Any, Optional

from app.core.interfaces import IDatabaseRepository, IAIService
from app.core.interfaces.query_normalizer import QueryNormalizer
from app.core.exceptions.tenant import TenantNotResolvedError
from app.core.config import settings

logger = logging.getLogger(__name__)

def now():
    return round(time.time() * 1000)


class AssistantService:
    """
    The Coordinator. Orchestrates the pipeline:
    Normalize -> Gate -> Classify -> Retrieve -> Generate
    
    Contains ZERO business logic. Only delegation.
    """

    def __init__(
        self, 
        db_repo: IDatabaseRepository, 
        ai_service: IAIService, 
        normalizer: QueryNormalizer = None,
        knowledge_repo = None,  # IKnowledgeRepository (optional for backward compat)
        knowledge_resolver = None,  # KnowledgeResolver (optional)
        tenant_context = None,  # TenantContextProvider (optional)
        # DI for Testing
        gate_service = None,
        intent_extractor = None,
        intent_classifier = None
    ):
        self.db = db_repo
        self.ai = ai_service
        
        # === DEPENDENCY INJECTION ===
        
        # Normalizer (Text Preprocessing)
        if normalizer:
            self.normalizer = normalizer
        else:
            from app.infrastructure.text.rule_based_normalizer import RuleBasedNormalizer
            self.normalizer = RuleBasedNormalizer()
        
        # Conversation Gate (Security/Filter Layer)
        # Conversation Gate (Security/Filter Layer)
        from app.core.services.conversation_gate import ConversationGate, GateDecision
        self.GateDecision = GateDecision
        
        if gate_service:
            self.gate = gate_service
        else:
            self.gate = ConversationGate()
        
        # Intent Extractor (Deterministic Classification)
        from app.core.services.intent_extractor import IntentExtractor, IntentType
        self.IntentType = IntentType
        
        if intent_extractor:
            self.intent_extractor = intent_extractor
        else:
            self.intent_extractor = IntentExtractor()
        
        # LLM-based Intent Classifier (Fallback for complex cases)
        if intent_classifier:
            self.intent_classifier = intent_classifier
        else:
            from app.core.services.intent_classifier import IntentClassifier
            self.intent_classifier = IntentClassifier(ai_service)
        
        # Reflex Agent (UX Layer - Conversational Fillers)
        from app.core.services.reflex_agent import ReflexAgent
        self.reflex_agent = ReflexAgent()
        
        # Prompt Provider (System Prompt Construction - SRP)
        from app.core.services.prompt_provider import PromptProvider
        self.prompt_provider = PromptProvider()
        
        # === NEW: Knowledge Layer (SaaS Architecture) ===
        
        # Knowledge Repository (Multi-Tenant Data Access)
        if knowledge_repo:
            self.knowledge_repo = knowledge_repo
        else:
            # Default: Create SqlKnowledgeRepository
            from app.infrastructure.database.knowledge_repository import SqlKnowledgeRepository
            from app.core.config import settings
            self.knowledge_repo = SqlKnowledgeRepository(settings.DB_NAME)
        
        # Knowledge Resolver (Semantic Routing)
        if knowledge_resolver:
            self.knowledge_resolver = knowledge_resolver
        else:
            # Default: Create with default providers
            from app.core.services.knowledge_resolver import KnowledgeResolver
            from app.infrastructure.providers.default_signal_providers import (
                DefaultScopeProvider, DefaultTopicProvider
            )
            self.knowledge_resolver = KnowledgeResolver(
                scope_provider=DefaultScopeProvider(),
                topic_provider=DefaultTopicProvider()
            )
        
        # Tenant Context (Multi-Tenant Session Management)
        if tenant_context:
            self.tenant_context = tenant_context
        else:
            # Default: Create StaticTenantContext for single-tenant mode
            from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
            self.tenant_context = StaticTenantContext("chinook_music")

    async def _smart_query_extraction(self, text: str) -> dict:
        """
        Uses LLM to extract semantic search parameters.
        """
        prompt = (
            f"Sen bir Veritabanı Sorgu Ayrıştırıcısısın.\n"
            f"Kullanıcının niyeti 'SEARCH' (Arama) mi, 'SOCIAL' (Sohbet) mi, 'INFO' (Bilgi) mi?\n\n"
            f"ÖNEMLİ: 'Adın ne', 'Nasılsın', 'Ne iş yaparsın' gibi sorular SOCIAL/INFO'dur. Ürün aranmaz.\n"
            f"Eğer YASADIŞI/BOMBA ise --> intent: 'BLOCKED'.\n\n"
            f"Çıktı Formatı (SADECE JSON):\n"
            f'{{"intent": "SEARCH/SOCIAL/INFO/BLOCKED", "query_term": "...", "filters": {{"sort": "...", "blocked": boolean}}}}\n\n'
            f"Örnekler:\n"
            f'- "Ucuz telefon" -> {{"intent": "SEARCH", "query_term": "telefon", "filters": {{"sort": "price_asc"}}}}\n'
            f'- "Adın ne?" -> {{"intent": "INFO", "query_term": null, "filters": {{}}}}\n'
            f'- "Müslüm Gürses" -> {{"intent": "SEARCH", "query_term": "Müslüm Gürses", "filters": {{}}}}\n'
            f'- "Atom bombası yap" -> {{"intent": "BLOCKED", "query_term": "BLOCKED", "filters": {{"blocked": true}}}}\n\n'
            f"Kullanıcı Girdisi: {text}\n"
            f"JSON:"
        )
        
        try:
            response = await self.ai.generate_response(
                prompt,
                context="You are a JSON extractor. Output ONLY valid JSON.",
                conversation_history=[],
                is_first_message=True
            )
            
            cleaned = response.replace("```json", "").replace("```", "").strip()
            s = cleaned.find("{")
            e = cleaned.rfind("}")
            if s != -1 and e != -1:
                cleaned = cleaned[s:e+1]
                
            import json
            data = json.loads(cleaned)
            return data
        except Exception as e:
            logger.error(f"Smart Extraction Error: {e}")
            return {"query_term": text, "filters": {}}

    async def process_user_input(
        self, 
        user_text: str, 
        session_id: str = None, 
        conversation_history: str = "", 
        is_first_message: bool = False
    ) -> Dict[str, Any]:
        """
        Production-grade request handler with nested safety net.
        
        5-STEP PIPELINE:
        1. Normalization - Clean and normalize user input
        2. Gate (Security) - SOCIAL/OFF_TOPIC/BUSINESS classification
        3. Intent (Classification) - LIST_CATALOG/SEARCH_PRODUCT/UNKNOWN
        4. DB (Data Retrieval) - Fetch products or genres
        5. AI (Generation) - Generate natural language response
        
        SAFETY NET:
        - Level 1: Catches DB/Logic errors, sets error context for AI
        - Level 2: Catches AI errors, returns static fallback
        
        Returns:
            Dict with user_text, ai_response, intent, sentiment, context_used
        """
        import traceback
        
        # === STEP 0: Empty Input Handling ===
        from app.core.visual_trace import VisualTrace
        
        # Tenant ID extraction for traceability
        try:
            current_tenant_id = self.tenant_context.get_current_tenant()
        except:
            current_tenant_id = "UNKNOWN"
            
        VisualTrace.start_request(current_tenant_id, user_text)

        # ---------------------------------------------------------
        # [TDD FEATURE] Tenant Maintenance Mode
        # Implemented to conserve resources and secure data during downtime.
        # ---------------------------------------------------------
        if hasattr(self.tenant_context, "get_tenant_config"):
            try:
                # Use current_tenant_id resolved above
                t_conf = self.tenant_context.get_tenant_config(current_tenant_id)
                if t_conf and t_conf.get("maintenance_mode"):
                    logger.warning(f"[MAINTENANCE] Tenant {current_tenant_id} is under maintenance. Blocking request.")
                    VisualTrace.log_step("Maintenance", "Sistem Bakımda", "İstek reddedildi.")
                    return {
                        "user_text": user_text,
                        "ai_response": "Üzgünüz, sistemimiz şu an bakım çalışması nedeniyle geçici olarak hizmet verememektedir. Lütfen daha sonra tekrar deneyiniz.",
                        "intent": "MAINTENANCE",
                        "sentiment": "NEUTRAL",
                        "context_used": "System Maintenance Mode"
                    }
            except Exception as e:
                logger.error(f"[MAINTENANCE] Check failed: {e}")
        # ---------------------------------------------------------

        if not user_text or not user_text.strip():
            return {
                "user_text": "",
                "ai_response": "",
                "intent": "SILENCE",
                "sentiment": "NEUTRAL",
                "context_used": ""
            }
            
        # [CAPABILITY LAYER] Setup - Non-Enforcing
        try:
            caps = self.tenant_context.get_capabilities()
            logger.debug(f"[CAPABILITY] Active: {caps.enabled}")
        except Exception:
            # Swallow errors in non-enforcing mode to preserve behavior
            pass
        
        t_start = now()
        context_data = ""
        intent_label = "DOMAIN"
        products = []
        
        # =========================================================
        # LEVEL 1: LOGIC & DATA LAYER PROTECTION
        # =========================================================
        try:
            # === STEP -1: IDENTITY RESOLUTION (Early Binding) ===
            tenant_id = self.tenant_context.get_current_tenant()
            tenant_info = self.knowledge_repo.get_tenant_info(tenant_id)
            logger.debug(f"[SERVICE] Identity Resolved: {tenant_info.get('ad', 'Unknown')}")
            
            # === STEP 0.5: Normalization ===
            normalized_text = self.normalizer.normalize(user_text)
            logger.debug(f"[SERVICE] Query: '{user_text}' -> Normalized: '{normalized_text}'")
            VisualTrace.log_step("Normalizer", "Metin temizlendi", f"{user_text} -> {normalized_text}")
            
            # === STEP 1: THE GATE (Security/Filter Check) ===
            if self.gate:
                gate_decision = self.gate.evaluate(user_text)
            else:
                # Fallback if no gate
                gate_decision = self.GateDecision.BUSINESS
            
            logger.info(f"Gate Log: {gate_decision}")
            VisualTrace.log_step("Gate", "Güvenlik Kapısı Kararı", gate_decision.name)
            
            # DEBUG PRINT
            print(f">>> DEBUG [Tenant]: {tenant_id}")
            print(f">>> DEBUG [Gate]: {gate_decision}")
            
            if gate_decision == self.GateDecision.BLOCKED:
                logger.warning(f"[SECURITY] Gate Blocked: {user_text}")
                VisualTrace.log_step("Security", "BLOCKED", "Yasadışı/Tehlikeli İstek")
                return {
                    "user_text": user_text,
                    "ai_response": "Üzgünüm, güvenlik ve etik kurallarımız gereği bu tür (tehlikeli/yasadışı) isteklere cevap veremiyorum. Lütfen başka bir konuda yardımcı olmama izin verin.",
                    "intent": "SECURITY_BLOCK",
                    "sentiment": "NEGATIVE",
                    "context_used": "Security Guardrail"
                }

            elif gate_decision == self.GateDecision.SOCIAL:
                logger.debug("[CONVERSATION_GATE] Decision: SOCIAL")
                context_data = "Kullanıcı sohbet ediyor. Samimi cevap ver."
                intent_label = "BLOCK_GREETING"
                # Skip DB, go directly to AI
                
            elif gate_decision == self.GateDecision.OFF_TOPIC:
                logger.debug("[CONVERSATION_GATE] Decision: OFF_TOPIC")
                context_data = "Kullanıcı konu dışı (off-topic) soru sordu. Kibarca reddet."
                intent_label = "BLOCK_OFF_TOPIC"
            
            else:
                # === STEP 2: INTENT CLASSIFICATION (HYBRID MODE) ===
                logger.debug("[CONVERSATION_GATE] Decision: BUSINESS -> Proceeding to Intent Classification")
                
                # 1. FAST PATH (Regex / Rule-Based) - < 1ms
                intent_result = self.intent_extractor.classify(normalized_text)
                VisualTrace.log_step("Intent (Fast)", "Regex Analizi", intent_result.intent.value)
                
                # 2. SMART PATH (LLM Fallback) - If Regex is unsure
                if intent_result.intent == self.IntentType.UNKNOWN:
                    logger.debug("[INTENT] Fast path UNKNOWN -> Invoking Smart Path (LLM)")
                    smart_intent_str = await self.intent_classifier.get_refined_intent(user_text)
                    VisualTrace.log_step("Intent (Smart)", "LLM Analizi", smart_intent_str)
                    
                    # Map LLM string to IntentType
                    from app.core.services.intent_extractor import IntentResult # Re-import if needed locally or use self
                    
                    if smart_intent_str == "LIST_CATALOG":
                        intent_result = IntentResult(intent=self.IntentType.LIST_CATALOG)
                    elif smart_intent_str == "INFORMATIONAL":
                         # Need to re-run KnowledgeResolver logic later, but setup basic Intent
                         # For now, treat as INFORMATIONAL intent, missing metadata might be issue
                         # Let's rely on basic Informational flow which uses KnowledgeResolver
                         # We need to inject 'raw_text' for resolver to work
                         intent_result = IntentResult(
                             intent=self.IntentType.INFORMATIONAL,
                             meta_data={"raw_text": normalized_text} 
                         )
                    elif smart_intent_str == "SOCIAL":
                         intent_result = IntentResult(intent=self.IntentType.SOCIAL)
                    else:
                          # SMART AI ENRICHMENT (The "Real Deal")
                          # We ask LLM to understand semantic intent (e.g., "Kelepir" -> sort: price_asc)
                          logger.debug("[ENRICH] Invoking LLM for Semantic Parameter Extraction...")
                          
                          # We'll use a fast, dedicated prompt for extraction
                          # This adds ~500ms latency but provides true intelligence
                          llm_intent = "SEARCH"
                          try:
                              extracted = await self._smart_query_extraction(normalized_text)
                              llm_intent = extracted.get("intent", "SEARCH")
                              q_term = extracted.get("query_term", normalized_text)
                              filters = extracted.get("filters", {})
                              VisualTrace.log_step("AI Enrichment", "Parametre Çıkarımı", f"Query: {q_term}, Filters: {filters}")
                              
                              # SECURITY CHECK
                              if filters.get("blocked"):
                                  logger.warning(f"[SECURITY] Request blocked: {normalized_text}")
                                  VisualTrace.log_step("Security", "BLOCKED", "Yasadışı/Tehlikeli İstek")
                                  
                                  # Immediate return bypassing everything
                                  from app.core.services.intent_extractor import IntentResult
                                  return {
                                      "user_text": user_text,
                                      "ai_response": "Üzgünüm, güvenlik ve etik kurallarımız gereği bu tür (tehlikeli/yasadışı) isteklere cevap veremiyorum. Lütfen başka bir konuda yardımcı olmama izin verin.",
                                      "intent": "SECURITY_BLOCK",
                                      "sentiment": "NEGATIVE",
                                      "context_used": "Security Guardrail"
                                  }

                          except Exception as e:
                              logger.error(f"[ENRICH] Failed: {e}")
                              q_term = normalized_text
                              filters = {}

                          
                          # Dynamic Intent Switching based on LLM
                          if llm_intent in ["INFO", "INFORMATIONAL"]:
                               intent_result = IntentResult(
                                  intent=self.IntentType.INFORMATIONAL,
                                  meta_data={"raw_text": normalized_text} 
                               )
                          elif llm_intent == "SOCIAL":
                               intent_result = IntentResult(intent=self.IntentType.SOCIAL)
                          else:
                               intent_result = IntentResult(
                                   intent=self.IntentType.SEARCH_PRODUCT,
                                   query_term=q_term,
                                   filters=filters
                               )
                
                logger.debug(f"[FINAL_INTENT] {intent_result.intent.value}")
                
                # === STEP 3: DATA RETRIEVAL (Based on Intent) ===
                if intent_result.intent == self.IntentType.LIST_CATALOG:
                    logger.debug("[SERVICE] CATALOG QUERY DETECTED - Fetching summary...") # List catalog
                    unique_categories = self.db.get_catalog_summary(tenant_id=tenant_id)
                    VisualTrace.log_db_result("get_catalog_summary", len(unique_categories) if unique_categories else 0, str(unique_categories))
                    
                    # Use centralized prompt builder
                    context_data = self.prompt_provider.build_system_context(
                        intent_result, 
                        unique_categories, # Pass categories as 'products'
                        conversation_history=conversation_history,
                        tenant_info=tenant_info
                    )
                    intent_label = "UNIVERSAL_CATALOG"
                
                elif intent_result.intent == self.IntentType.INFORMATIONAL:
                    # ================================================================
                    # INFORMATIONAL INTENT: Company Knowledge (NOT Product Search!)
                    # ================================================================
                    
                    raw_text = intent_result.meta_data.get("raw_text", normalized_text)
                    
                    # Step 1: Resolve knowledge request
                    knowledge_request = self.knowledge_resolver.resolve(
                        user_text=raw_text,
                        intent_metadata=intent_result.meta_data
                    )
                    
                    logger.debug(f"[SERVICE] INFORMATIONAL Intent - Scope: {knowledge_request.scope}, "
                                 f"Target: {knowledge_request.target}, Topic: {knowledge_request.topic_key}")
                    
                    # Step 3: Fetch from knowledge repository (tenant-isolated)
                    company_info = None
                    if knowledge_request.target == "knowledge":
                        try:
                            company_info = self.knowledge_repo.get(
                                tenant_id=tenant_id,
                                topic_key=knowledge_request.topic_key
                            )
                        except Exception as e:
                            logger.error(f"[SERVICE] Knowledge fetch error: {e}")
                            VisualTrace.log_step("Database", "Bilgi Getirme Hataso", str(e))
                    
                    # Step 4: Build context
                    if company_info:
                        context_data = f"ŞİRKET BİLGİSİ ({knowledge_request.topic_key.upper()}): {company_info}"
                        VisualTrace.log_db_result("KnowledgeRepo.get", 1, company_info[:50] + "...")
                    else:
                        # Fallback: Let AI handle naturally
                        context_data = f"Kullanıcı şirket hakkında bilgi istiyor (konu: {knowledge_request.topic_key}). Uygun bir şekilde cevapla."
                    
                    intent_label = "INFORMATIONAL"
                    
                elif intent_result.intent == self.IntentType.SEARCH_PRODUCT:
                    search_term = intent_result.query_term
                    is_wildcard = search_term is None
                    sort_filter = intent_result.filters.get('sort', '')
                    logger.debug(f"[SERVICE] SEARCH_PRODUCT - Searching for: '{search_term}' with filters={intent_result.filters}")
                    
                    products = self.db.search_products(
                        search_term, 
                        limit=5, 
                        filters=intent_result.filters,
                        tenant_id=tenant_id
                    )
                    VisualTrace.log_db_result("search_products", len(products), str([p.name for p in products]))
                    
                    # Use centralized prompt builder with strict constraints
                    context_data = self.prompt_provider.build_system_context(
                        intent_result, 
                        products, 
                        sort_filter, 
                        is_wildcard,
                        conversation_history=conversation_history,  # Pass history 
                        tenant_info=tenant_info                   # NEW: Pass Identity
                    )
                    
                    if products:
                        logger.debug(f"[SERVICE] Products Found: {len(products)}")
                        for p in products[:3]:
                            logger.debug(f"   - {p.name} | {p.price} USD")
                    
                    intent_label = "UNIVERSAL_RAG"
                
                elif intent_result.intent == self.IntentType.SOCIAL:
                    # SOCIAL Intent - Use centralized prompt builder
                    subtype = intent_result.meta_data.get("subtype", "casual_chat")
                    logger.debug(f"[SERVICE] SOCIAL Intent - Subtype: {subtype}")
                    
                    context_data = self.prompt_provider.build_system_context(
                        intent_result, 
                        products=[], 
                        sort_filter='', 
                        is_wildcard=False, 
                        conversation_history=conversation_history,
                        tenant_info=tenant_info                   # NEW: Pass Identity
                    )
                    
                    intent_label = f"SOCIAL_{subtype.upper()}"
                    
                elif intent_result.intent == self.IntentType.UNKNOWN:
                    # Store context
                    if products:
                        # Format as explicit Turkish text for the AI
                        lines = ["BULUNAN ÜRÜNLER:"]
                        for p in products:
                            lines.append(f"- Ürün: {p.name} | Fiyat: {p.price} {p.currency} | Açıklama: {p.description}")
                        context_data = "\n".join(lines)
                    else:
                        context_data = "Veritabanında eşleşen ürün bulunamadı."
                    context_data = "Kullanıcı bir ürün arıyor ama ne olduğu anlaşılamadı. Yardım iste."
                    intent_label = "UNKNOWN"
            
            # === SAAS IDENTITY INJECTION ===
            # Ensure context contains company info if not already processed by PromptProvider
            # (Note: PromptProvider handles identity now, but we verify here)
            final_context_data = context_data
            
            # LOG THE SYSTEM PROMPT
            if "You are Melody" in final_context_data:
                VisualTrace.log_prompt_snapshot(final_context_data)
            else:
                 VisualTrace.log_step("Prompt", "Context Data Hazırlandı", f"{tenant_info.get('ad')} için context oluşturuldu.")

            print(f"========================================")
            print(f"SEARCH DONE: {now() - t_start} ms | Found (Prods): {len(products)}")
            
            # === STEP 4: REFLEX AGENT (UX Layer) ===
            filler = await self.reflex_agent.get_filler(intent_label)
            if filler:
                logger.debug(f"[REFLEX_AGENT] Filler: '{filler}'")
                
                
        except TenantNotResolvedError:
            # CRITICAL: Do NOT catch this. It must bubble up to stop execution.
            # Missing tenant is a configuration/security error, not a runtime glitch.
            raise
            
        except Exception as e:
            # =========================================================
            # LEVEL 1 ERROR HANDLER: Logic/Data Layer Failure
            # =========================================================
            print(f"!!! APP ERROR (Data/Logic Layer) !!!: {str(e)}")
            traceback.print_exc()
            
            # RECOVERY: Inform AI about the failure so it can apologize gracefully
            context_data = "SİSTEM HATASI: Veritabanına veya arama servisine şu an ulaşılamıyor. Kullanıcıdan kibarca özür dile."
            intent_label = "ERROR_RECOVERY"
        
        # =========================================================
        # LEVEL 2: AI LAYER PROTECTION
        # =========================================================
        try:
            # === STEP 5: AI RESPONSE GENERATION ===
            ai_response = await self.ai.generate_response(
                user_text,
                context=context_data,
                conversation_history=conversation_history,
                is_first_message=is_first_message
            )
            
            return {
                "user_text": user_text,
                "ai_response": ai_response,
                "intent": intent_label,
                "sentiment": "NEUTRAL",
                "context_used": context_data
            }
            
        except Exception as ai_error:
            # =========================================================
            # LEVEL 2 ERROR HANDLER: AI Layer Critical Failure
            # =========================================================
            print(f"!!! CRITICAL AI ERROR !!!: {str(ai_error)}")
            traceback.print_exc()
            
            # FALLBACK: Static "Safe Mode" message (No AI required)
            return {
                "user_text": user_text,
                "ai_response": "Üzgünüm, şu an servislerime erişemiyorum. Lütfen biraz sonra tekrar deneyin.",
                "intent": "CRITICAL_FALLBACK",
                "sentiment": "NEUTRAL",
                "context_used": "SAFE_MODE"
            }


    async def process_user_input_stream(
        self, 
        user_text: str, 
        session_id: str, 
        conversation_history: str, 
        memory: Any = None
    ):
        """
        Streaming version for voice output.
        Uses same pipeline but streams AI output -> TTS.
        """
        # Simplified retrieval for streaming
        normalized_text = self.normalizer.normalize(user_text)
        intent_result = self.intent_extractor.classify(normalized_text)
        
        if intent_result.intent == self.IntentType.LIST_CATALOG:
            genres = self.db.get_unique_genres()
            context_data = f"MEVCUT MÜZİK TÜRLERİ: {', '.join(genres)}" if genres else ""
        elif intent_result.intent == self.IntentType.SEARCH_PRODUCT:
            products = self.db.search_products(intent_result.query_term or normalized_text, limit=5)
            context_data = "BULUNAN ÜRÜNLER:\n" + "\n".join([p.to_context_string() for p in products]) if products else ""
        else:
            context_data = ""
        
        # Streaming Pipeline
        import edge_tts
        
        # Silent primer for audio sync
        yield bytes([0xFF, 0xFB, 0x90, 0x00] + [0x00] * 44) * 3
        
        buffer = ""
        full_ai_response = ""
        
        async for text_chunk in self.ai.generate_response_stream(
            user_text,
            context=context_data,
            conversation_history=conversation_history
        ):
            buffer += text_chunk
            full_ai_response += text_chunk
            
            # Sentence splitting for TTS
            sentences = re.split(r'(?<=[.!?])\s+', buffer)
            if len(sentences) > 1:
                to_speak = sentences[:-1]
                buffer = sentences[-1]
                for s in to_speak:
                    if len(s.strip()) > 2:
                        communicate = edge_tts.Communicate(s, settings.SES_MODELI)
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                yield chunk["data"]
        
        # Flush remaining buffer
        if buffer.strip():
            communicate = edge_tts.Communicate(buffer, settings.SES_MODELI)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        
        # Memory logging
        if memory:
            memory.add_turn(user_text, full_ai_response)
        
        try:
            self.db.log_call(user_text, full_ai_response, "NEUTRAL", None, intent="UNIVERSAL_RAG")
        except Exception:
            pass

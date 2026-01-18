from groq import AsyncGroq
import asyncio
from app.core.interfaces import IAIService
# Removed COMPANY_INFO import
from typing import Dict, Any, Optional, AsyncIterator
import json
import re

class GroqAIService(IAIService):
    def __init__(self, api_key: str, model_name: str = "llama-3.1-8b-instant"):
        self.client = AsyncGroq(api_key=api_key)
        self.model_name = model_name
        self.fast_model = "llama-3.1-8b-instant"
        # self.company_info removed to ensure STATELESS SaaS architecture
        self.company_identity = "Kayıtlı Şirket" # Default fallback
        self.db_schema = None

    def set_db_schema(self, schema: str):
        """Store DB schema for AI context"""
        self.db_schema = schema

    async def _call_api_with_retry(self, messages, model, temperature=0.1, response_format=None):
        max_retries = 3
        delay = 2
        for attempt in range(max_retries):
            try:
                kwargs = { "messages": messages, "model": model, "temperature": temperature }
                if response_format: kwargs["response_format"] = response_format
                return await self.client.chat.completions.create(**kwargs)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise e
        raise Exception("Maksimum deneme sayısına ulaşıldı.")

    async def determine_intent(self, user_text: str) -> str:
        # Simplified intent logic for compatibility
        return "UNIVERSAL_RETRIEVAL"

    async def analyze_sentiment(self, user_text: str) -> str:
        return "NEUTRAL"

    async def generate_command(self, user_text: str) -> Dict[str, Any]:
        return {"action": "QUERY_DB", "params": {}}

    def _get_system_prompt(self, context: Any = None) -> str:
        # PURE SAAS LOGIC: Identity must come from context, otherwise use generic persona.
        company_segment = ""
        identity_intro = "Sen yardımcı bir sesli asistansın."
        
        # Check if context already defines identity (from PromptProvider)
        if context and isinstance(context, str) and "IDENTITY" in context:
            identity_intro = "" # Let context override identity
        
        return f"""
        KİMLİK:
        {identity_intro}
        Görevin müşterilere veritabanındaki bilgiler hakkında yardımcı olmaktır.
        Sana verilen 'BİLGİ KAYNAĞI' içindeki verilere sadık kalarak, sanki o şirketin çalışanıymışsın gibi konuş.

        ORTAM:
        - Telefon görüşmesindesin.
        - GÖRSEL TERİMLER YASAK (Klikle, Link, Buton, Liste, Menü).
        - Kısa, net ve PROFESYONEL konuş.

        BİLGİ KAYNAĞI (UNIVERSAL RETRIEVAL):
        Sana kullanıcı sorusuyla birlikte kaynak veriler (potansiyel ürünler veya şirket bilgisi) verilecek.
        [BULUNAN ÜRÜNLER / BİLGİLER] bölümündeki bilgileri kullanarak cevap ver.
        - Eğer şirket bilgisi verilmişse, o bilgiyi TARTIŞMASIZ doğru kabul et ve kullanıcıya sun.
        - Fiyat sorulursa, oradaki "Price" bilgisini oku.
        - Stok sorulursa, "is_in_stock" bilgisine bak.
        - Detay sorulursa "Description" kısmını özetle.

        AKILLİ YORUMLAMA (ÇOK ÖNEMLİ):
        Ses tanıma hatalarını tölere et (örn. "mücük" -> "müzik").
        Bağlamı koru.

        KURALLAR:
        1. SİPARİŞ YASAK: Asla sipariş alma. Web sitesine yönlendir.
        2. FİYAT: Listede ne varsa onu söyle.
        3. REDDETME: Tehlikeli konularda bilgi verme.
        4. HALÜSİNASYON YOK: Kayıtlarda olmayan şeyi uydurma.
        5. SOHBET MODU: Genel sohbet edilebilir, ama kısa tut.
        6. SAADET (SAAS UYUMLULUĞU): Asla kendini belirli bir şirketle sınırlama, o anki BİLGİ KAYNAĞI hangi şirketi işaret ediyorsa onu temsil et.
        7. GÖREVE ODAKLA: Kişisel sorular gelirse (renk, yaş vb.), "Ben bir asistanım" de ve konuyu işe getir.
        8. UZATMA: Cevapların maksimum 1-2 cümle olsun.
        9. BAĞLAM ANALİZİ: Kullanıcının ne demek istediğini benzer kelimelerden anlayabilirsin.
        
        {company_segment}
        """
    async def generate_response_stream(self, user_text: str, context: Any = None, conversation_history: str = "") -> AsyncIterator[str]:
        system_prompt = self._get_system_prompt(context)
        
        user_prompt = user_text
        if context:
            user_prompt += f"\n\n[BULUNAN ÜRÜNLER]:\n{context}"
        
        try:
            stream = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                temperature=0.3,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception:
            yield "Bağlantı hatası oluştu."

    async def generate_response(self, user_text: str, context: Any = None, conversation_history: str = "", is_first_message: bool = False) -> str:
        system_prompt = self._get_system_prompt(context)
        if is_first_message:
            system_prompt += "\nNOT: Bu görüşmenin başı. Nazikçe kendini tanıt (Melody)."
            
        user_prompt = user_text
        if context:
             user_prompt += f"\n\n[BULUNAN ÜRÜNLER]:\n{context}"
             
        try:
            resp = await self._call_api_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                temperature=0.3
            )
            return resp.choices[0].message.content
        except Exception:
            return "Şu an yanıt veremiyorum."

    def generate_command(self, user_text: str):
        # Dummy implementation for Interface compliance
        return {}

    async def generate_summary(self, conversation_text: str) -> str:
        """
        Summarizes the conversation for Database logs.
        """
        try:
            prompt = f"Aşağıdaki konuşmayı kısaca özetle (Tek cümle):\n\n{conversation_text}"
            
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model=self.model_name,
                max_tokens=60,
                temperature=0.3,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Summary Error: {e}")
            return "Özet oluşturulamadı."

    async def classify_text(self, system_prompt: str, user_text: str) -> str:
        """
        Raw classification call. Uses Temp=0.0 for determinism.
        """
        try:
            resp = await self._call_api_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                model=self.fast_model, # Use generic fast model
                temperature=0.0 # Strict classification
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"Classification Error: {e}")
            return "DOMAIN" # Fail safe fallback

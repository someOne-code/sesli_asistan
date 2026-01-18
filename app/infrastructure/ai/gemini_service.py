from google import genai
from app.core.interfaces import IAIService
from app.core.config import COMPANY_INFO
from typing import Dict, Any, Optional
import json
import re

class GeminiAIService(IAIService):
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.company_info = COMPANY_INFO
        self.company_identity = self.company_info["ad"]
        self.db_schema = "Veritabanı şeması yükleniyor..."

    def set_db_schema(self, schema_summary: str):
        self.db_schema = schema_summary

    async def determine_intent(self, user_text: str) -> str:
        prompt = f"""
        NİYET SINIFLANDIRMA (STRICT MODE)
        Amacımız: Sadece Müzik Mağazası ile ilgili konularda yardımcı olmak.

        Girdiyi şu kategorilerden BİRİNE sınıflandır:

        1. **MUSIC_SEARCH**
        Müzik, şarkı, albüm, sanatçı, fiyat, stok veya müzik türü arama.

        2. **COMPANY_INFO**
        Şirket adresi, telefonu, vizyonu, misyonu, çalışma saatleri veya "siz kimsiniz" gibi sorular.

        3. **GENERAL_CHAT**
        Selamlaşma, hal hatır sorma veya müzik/şirket dışı genel sohbet.

        SADECE KATEGORİ ADINI DÖNDÜR (Örn: MUSIC_SEARCH). BAŞKA HİÇBİR ŞEY YAZMA.
        
        Girdi: "{user_text}"
        Kategori:
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            intent = response.text.strip().upper()
            
            # Temizlik
            if "MUSIC_SEARCH" in intent: return "MUSIC_SEARCH"
            if "COMPANY_INFO" in intent: return "COMPANY_INFO"
            return "GENERAL_CHAT"
        except Exception:
            return "GENERAL_CHAT"

    async def analyze_sentiment(self, user_text: str) -> str:
        prompt = f"""
        Şu metnin duygu durumunu analiz et: "{user_text}"
        Sadece tek kelime döndür: POSITIVE, NEUTRAL veya NEGATIVE.
        Baska hicbir sey yazma.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            sentiment = response.text.strip().upper()
            if "POSITIVE" in sentiment: return "POSITIVE"
            if "NEGATIVE" in sentiment: return "NEGATIVE"
            return "NEUTRAL"
        except Exception:
            return "NEUTRAL"

    async def generate_command(self, user_text: str) -> Dict[str, Any]:
        # Intent kontrolü dışarıda yapılıyor, burada direk komut üret.
        
        prompt = f"""
        Veritabanı Şeması:
        {self.db_schema}

        Kullanıcı İsteği: "{user_text}"

        Görevin: Kullanıcı isteğini SQL sorgusu oluşturacak parametrelere dönüştür.
        
        Çıktı Formatı (JSON):
        {{
            "action": "SEARCH_MUSIC",
            "params": {{
                "genre": "Pop", // Opsiyonel
                "artist": "Queen", // Opsiyonel
                "album": "A Kind of Magic", // Opsiyonel
                "max_price": 1.99, // Opsiyonel
                "limit": 5 // Varsayılan 5
            }}
        }}
        
        SADECE JSON DÖNDÜR.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            # JSON temizliği (Markdown backtickleri kaldır)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text)
        except Exception as e:
            print(f"Gemini Command Error: {e}")
            return {"action": "UNKNOWN", "params": {}}

    async def generate_response(self, user_text: str, context: Any = None, conversation_history: str = "") -> str:
        # Şirket bilgilerini formatlı string yap
        company_info_str = f"""
        Şirket Adı: {self.company_info['ad']}
        Asistan Adı: {self.company_info['asistan_adi']}
        Slogan: {self.company_info['slogan']}
        Misyon: {self.company_info['misyon']}
        Vizyon: {self.company_info['vizyon']}
        Telefon: {self.company_info['iletisim']['telefon']}
        E-posta: {self.company_info['iletisim']['email']}
        Adres: {self.company_info['iletisim']['adres']}
        Çalışma Saatleri: {self.company_info['calisma_saatleri']}
        """

        system_prompt = f"""
        ROL: Sen {self.company_info['asistan_adi']} adında, {self.company_identity} için çalışan KURUMSAL bir satış asistanısın.
        Görevin: Müzik veritabanındaki ürünleri satmak, şirket hakkında bilgi vermek.
        
        ========== ŞİRKET BİLGİLERİ (Kullanıcıya Verilebilir) ==========
        {company_info_str}
        ================================================================

        VERİTABANI BİLGİSİ:
        {self.db_schema}

        ========== GEÇMİŞ KONUŞMALAR (HAFIZA) ==========
        {conversation_history if conversation_history else "Henüz bir konuşma yok. Bu ilk mesaj."}
        ================================================

        KESİN KURALLAR:
        1. Kısa ve hedefe yönelik cevaplar ver.
        2. Şirket hakkında sorulursa (adı, misyonu, iletişim vb.) yukarıdaki bilgileri MUTLAKA ver.
        3. Adın sorulursa "{self.company_info['asistan_adi']}" de.
        4. Müzik veya şirket dışı sorulara nazikçe "Sadece müzik ve şirketimiz konusunda yardımcı olabilirim" de.
        5. Fiyat veya ürün bilgisi verirken net ol.
        
        **** KRİTİK SELAMLAŞMA KURALI ****
        YUKARIDAKİ "GEÇMİŞ KONUŞMALAR" bölümüne bak.
        - Eğer orada zaten bir selam (Merhaba, Nasılsın, vb.) GEÇTİYSE:
          TEKRAR "Merhaba", "Selam", "Hoş geldiniz" DEME!
          DİREKT KONUYA GİR.
        - Eğer "Henüz bir konuşma yok" yazıyorsa, bu ilk mesajdır, o zaman selam verebilirsin.
        *************************************

        TON: Profesyonel, Kibar, Satış Odaklı, Türkçe.
        """
        
        full_prompt = f"{system_prompt}\n\nMüşteri: {user_text}\n"
        if context:
            full_prompt += f"Bağlam/Veri: {context}\n"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"GEMINI GENERATE ERROR: {e}")
            return "Şu an cevap veremiyorum."

    async def generate_summary(self, conversation_history: str) -> str:
        if not conversation_history:
            return "Özet oluşturulamadı."
            
        prompt = f"""
        Aşağıdaki müşteri-asistan görüşmesini 3 cümlede özetle.
        Odaklan: Müşteri ne sordu? Asistan ne cevap verdi? Sonuç ne oldu?
        
        GÖRÜŞME:
        {conversation_history}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception:
            return "Summary generation failed."

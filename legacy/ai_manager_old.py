import logging
from groq import AsyncGroq
from config import settings, logger
from database import DatabaseManager
from utils import TextUtils
from typing import Optional

class AIManager:
    def __init__(self, db_manager: DatabaseManager):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.db = db_manager
        self.company_identity: str = "Profesyonel Asistan" # Default
        self.system_prompt_base: str = ""

    async def initialize_persona(self) -> None:
        """Determines company identity based on DB content or falls back to default."""
        try:
            logger.info("Initializing Company Identity...")
            # We hardcode or simplify this to avoid raw data access if needed, 
            # but for now, we keep it simple or use a static one.
            # Assuming Music Store context for now to be safe.
            self.company_identity = "TechFix Music Assistant"
            logger.info(f"Identity Set: {self.company_identity}")

        except Exception as e:
            logger.error(f"Failed to generate identity: {e}. Using fallback.")
            self.company_identity = "Profesyonel Müşteri Hizmetleri Asistanı"

    async def determine_intent(self, user_text: str) -> str:
        """Decides if the user wants Music Search, company info, or just chat."""
        try:
            prompt = f"""
            INTENT CLASSIFICATION
            Classify the input into ONE of these categories:

            1. **MUSIC_SEARCH** Intent
            User is asking for data about:
            - Music tracks, albums, artists, composers
            - Prices (cheapest, most expensive)
            - Genres (rock, pop, jazz, etc.)
            - Searching for songs
            
            2. **CHAT** Intent
            User is making casual conversation:
            - Greetings (hello, hi, how are you)
            - General music preferences
            - Feedback
            
            3. **COMPANY_INFO** Intent
            User is asking specifically about:
            - Company vision, mission, services
            
            4. **OUT_OF_SCOPE** Intent
            User is asking about topics unrelated to music services OR Sensitive Data:
            - Mathematics, homework
            - Personal life, politics
            - **SENSITIVE DATA**: Invoices, Customer details, Employee info, Sales numbers. (STRICTLY FORBIDDEN)

            Input: "{user_text}"
            
            Return ONLY the label (MUSIC_SEARCH, CHAT, COMPANY_INFO, or OUT_OF_SCOPE).
            """
            resp = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            return "CHAT" # Fail-safe

    async def analyze_sentiment(self, user_text: str) -> str:
        """Analyzes the sentiment of the user text."""
        try:
            prompt = f"""
            Analyze sentiment of: "{user_text}"
            Return ONLY one word: POSITIVE, NEUTRAL, or NEGATIVE.
            """
            resp = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return "NEUTRAL"

    async def generate_summary(self, conversation_history: str) -> str:
        """Generates a summary of the conversation."""
        if not conversation_history:
            return "No conversation."
        try:
            prompt = f"""
            Summarize the following call notes briefly:
            {conversation_history}
            """
            resp = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.3
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return "Summary generation failed."

    async def generate_command(self, user_text: str) -> dict:
        """
        Generates a structured command for the SafeService layer.
        Replaces direct SQL generation.
        """
        prompt = f"""
        You are a smart command parser for a Music Service.
        The user wants to find music.
        
        Available Actions:
        - SEARCH_TRACKS (params: keyword) -> for song names or composers
        - GET_TRACKS_BY_GENRE (params: genre_name) -> for 'rock', 'pop' queries
        - GET_ALBUM_DETAILS (params: album_name)
        - GET_CHEAPEST (params: None)
        - GET_MOST_EXPENSIVE (params: None)
        
        User Input: "{user_text}"
        
        Output a JSON object ONLY:
        {{
            "action": "ACTION_NAME",
            "params": {{ "param_name": "value" }}
        }}
        """
        try:
            resp = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            import json
            return json.loads(resp.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"Command generation failed: {e}")
            return {"action": "UNKNOWN", "params": {}}

    async def generate_response(self, user_text: str, context: str = "") -> str:
        """Generates the final natural language response."""
        
        system_prompt = f"""
        ROLE: You are the professional assistant for {self.company_identity}.
        
        RESPONSE GUIDELINES
        
        1. **For SQL Results (Context provided):**
           - Convert results into friendly, natural language.
           - Include relevant details (prices, names, counts).
           - Be conversational, not technical.
           - Example: "The cheapest track is 'X' at $0.99."
           
        2. **For CHAT Intent (No Data Context):**
           - Respond naturally and friendly.
           - Show enthusiasm about music.
           - Offer to help with specific queries.
           - Keep responses concise.
           
        3. **For COMPANY_INFO Intent:**
           - Explain the company's music service offerings.
           - Highlight the catalog (tracks, albums, artists, genres).
           - Be professional and informative.
           
        4. **For OUT_OF_SCOPE Intent:**
           - Politely decline.
           - Redirect to music-related topics.
           - Maintain friendly tone.

        TONE & STYLE:
        ✅ **Do:**
        - Be friendly, warm, and professional
        - Use conversational language (Turkish)
        - Show enthusiasm for music
        - Provide clear, concise answers
        
        ❌ **Don't:**
        - Use technical jargon (SQL, database, schema)
        - Be robotic or overly formal
        - Provide incomplete information
        """
        
        if context == "COMPANY_INFO_REQUEST":
            user_prompt = f"""
            Customer: "{user_text}"
            Intent: COMPANY_INFO
            Task: Provide company service info in Turkish.
            """
        elif context == "OUT_OF_SCOPE":
            user_prompt = f"""
            Customer: "{user_text}"
            Intent: OUT_OF_SCOPE
            Task: Politely decline in Turkish.
            """
        elif context:
            user_prompt = f"""
            Customer: "{user_text}"
            Intent: SQL (Data Provided)
            Data/Context: "{context}"
            
            Instructions:
            1. Use the Data to answer.
            2. If Data is 'ÜRÜN_KATEGORISI_YOK', say we don't sell that.
            3. If Data is 'HATA', say there's a system issue.
            4. If Data is a list, summarize it nicely in Turkish.
            """
        else:
            user_prompt = f"""
            Customer: "{user_text}"
            Intent: CHAT
            Task: Answer naturally in friendly, short sentences (Turkish).
            """

        try:
            final_resp = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.5
            )
            return TextUtils.clean_text_for_tts(final_resp.choices[0].message.content)
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "Şu an cevap veremiyorum, lütfen biraz sonra tekrar deneyin."

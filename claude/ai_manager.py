"""
AI Manager - Refactored with Zero-Knowledge Architecture
AI only knows about public music catalog, cannot generate SQL.
"""

import logging
import json
from groq import Groq
from config import settings, logger, LogEmoji
from safe_service import SafeService
from utils import TextUtils
from typing import Optional, Dict, Any


class AIManager:
    """
    Manages all AI operations with strict data isolation.
    AI operates in zero-knowledge environment for sensitive data.
    """
    
    def __init__(self, safe_service: SafeService):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.safe_service = safe_service
        self.company_identity: str = settings.DEFAULT_COMPANY_NAME
        
        # AI only sees public schema
        self.public_schema = safe_service.get_public_schema()
    
    def initialize_persona(self) -> None:
        """Determines company identity (only uses public data)"""
        try:
            logger.info(f"{LogEmoji.MASK} Initializing Company Identity...")
            
            # Get sample public data only
            sample_genres = self.safe_service.list_genres()
            
            if not sample_genres:
                logger.warning(f"{LogEmoji.WARNING} No data found for identity generation. Using default.")
                return
            
            genre_list = ", ".join([g['GenreName'] for g in sample_genres[:5]])
            
            prompt = f"""Based on this music service with genres: {genre_list}, create a brief company identity (1-2 sentences).
Focus on music catalog services.

Respond in Turkish with a professional description."""
            
            resp = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.RESPONSE_GENERATION_MODEL,
                temperature=settings.RESPONSE_TEMPERATURE
            )
            
            self.company_identity = resp.choices[0].message.content.strip()
            logger.info(f"{LogEmoji.CHECK} Identity Generated: {self.company_identity}")
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Failed to generate identity: {e}. Using fallback.")
            self.company_identity = "Profesyonel Müzik Hizmetleri Asistanı"
    
    def determine_intent(self, user_text: str) -> str:
        """
        Classifies user intent with explicit boundaries.
        AI knows it cannot access sensitive data.
        """
        try:
            prompt = f"""You are a music catalog assistant. Classify the user's intent.

YOUR SCOPE (What you CAN help with):
- Music catalog queries (albums, artists, tracks, genres, playlists)
- Music recommendations
- Pricing information for music
- General music-related chat

STRICTLY OUT OF SCOPE (You CANNOT access):
- Customer information or personal data
- Employee information
- Invoice or financial records
- Sales reports or transaction history
- Any sensitive business data

INTENT CATEGORIES:

**MUSIC_QUERY** - User wants music catalog information:
Examples: "rock albums", "cheapest track", "AC/DC albums", "jazz playlists"

**CHAT** - General conversation about music:
Examples: "hello", "thank you", "I like rock music"

**COMPANY_INFO** - About the service itself:
Examples: "what do you offer", "tell me about your service"

**FORBIDDEN_DATA** - User asking for sensitive data you DON'T have access to:
Examples: "customer list", "invoice #123", "employee addresses", "sales report", "who bought what"

**OUT_OF_SCOPE** - Completely unrelated topics:
Examples: "weather", "math problem", "political question"

User Input: "{user_text}"

Return ONLY ONE WORD: MUSIC_QUERY, CHAT, COMPANY_INFO, FORBIDDEN_DATA, or OUT_OF_SCOPE"""
            
            resp = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.INTENT_CLASSIFICATION_MODEL,
                temperature=settings.INTENT_TEMPERATURE
            )
            
            intent = resp.choices[0].message.content.strip().upper()
            
            valid_intents = ["MUSIC_QUERY", "CHAT", "COMPANY_INFO", "FORBIDDEN_DATA", "OUT_OF_SCOPE"]
            if intent not in valid_intents:
                logger.warning(f"{LogEmoji.WARNING} Invalid intent '{intent}', defaulting to CHAT")
                return "CHAT"
            
            return intent
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Intent detection failed: {e}")
            return "CHAT"
    
    def analyze_sentiment(self, user_text: str) -> str:
        """Analyzes sentiment (unchanged)"""
        try:
            prompt = f"""Analyze sentiment: "{user_text}"
Return ONLY: POSITIVE, NEUTRAL, or NEGATIVE"""
            
            resp = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.SENTIMENT_ANALYSIS_MODEL,
                temperature=settings.SENTIMENT_TEMPERATURE
            )
            
            sentiment = resp.choices[0].message.content.strip().upper()
            return sentiment if sentiment in ["POSITIVE", "NEUTRAL", "NEGATIVE"] else "NEUTRAL"
        
        except Exception as e:
            logger.warning(f"{LogEmoji.WARNING} Sentiment analysis failed: {e}")
            return "NEUTRAL"
    
    def generate_summary(self, conversation_history: str) -> str:
        """Generates conversation summary (unchanged)"""
        if not conversation_history or len(conversation_history) < 10:
            return "Konuşma içeriği yok."
        
        try:
            prompt = f"""Summarize this conversation in 2-3 sentences (Turkish):

{conversation_history}"""
            
            resp = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.SUMMARY_GENERATION_MODEL,
                temperature=settings.SUMMARY_TEMPERATURE
            )
            
            return resp.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Summary generation failed: {e}")
            return "Özet oluşturulamadı."
    
    def parse_music_query(self, user_text: str, context_history: str = "") -> Dict[str, Any]:
        """
        AI no longer generates SQL. Instead, it outputs structured actions.
        The service layer will execute these actions with parameterized queries.
        """
        try:
            prompt = f"""{self.public_schema}

Conversation History:
{context_history}

Current Question: "{user_text}"

YOUR TASK:
Analyze the question and output a structured action command.

AVAILABLE ACTIONS:
- SEARCH_TRACKS: Search tracks by keyword
- SEARCH_ALBUMS: Search albums by keyword
- SEARCH_ARTISTS: Search artists by keyword
- GET_ARTIST_ALBUMS: Get albums by artist name
- GET_TRACKS_BY_GENRE: Get tracks filtered by genre
- GET_ALBUM_DETAILS: Get details of specific album
- GET_CHEAPEST_TRACKS: Get cheapest tracks (optionally by genre)
- GET_MOST_EXPENSIVE_TRACKS: Get most expensive tracks (optionally by genre)
- LIST_GENRES: List all genres
- LIST_MEDIA_TYPES: List all media types
- NOT_AVAILABLE: The requested data is not in your scope

OUTPUT FORMAT (JSON only, no explanation):
{{
    "action": "ACTION_NAME",
    "params": {{
        "keyword": "search term",
        "limit": 5,
        "genre": "Rock"
    }},
    "reasoning": "brief explanation"
}}

CRITICAL RULES:
1. You can ONLY access music catalog tables listed in schema
2. You CANNOT access: Customer, Employee, Invoice, InvoiceLine, call_logs
3. If user asks for forbidden data, return: {{"action": "NOT_AVAILABLE"}}
4. Return ONLY valid JSON, nothing else

Examples:
- "cheapest rock tracks" → {{"action": "GET_CHEAPEST_TRACKS", "params": {{"genre": "Rock", "limit": 5}}}}
- "AC/DC albums" → {{"action": "GET_ARTIST_ALBUMS", "params": {{"artist_name": "AC/DC", "limit": 10}}}}
- "customer invoices" → {{"action": "NOT_AVAILABLE", "reasoning": "Customer data not accessible"}}

Now process: "{user_text}"
"""
            
            resp = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.SQL_GENERATION_MODEL,
                temperature=settings.SQL_TEMPERATURE
            )
            
            response_text = resp.choices[0].message.content.strip()
            
            # Extract JSON from response
            # Remove markdown code blocks if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            action_data = json.loads(response_text)
            
            logger.info(f"{LogEmoji.SEARCH} Action parsed: {action_data.get('action')}")
            return action_data
        
        except json.JSONDecodeError as e:
            logger.error(f"{LogEmoji.ERROR} Failed to parse action JSON: {e}")
            return {"action": "NOT_AVAILABLE", "error": "parse_error"}
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Query parsing failed: {e}")
            return {"action": "NOT_AVAILABLE", "error": str(e)}
    
    def generate_response(self, user_text: str, context: str = "", intent: str = "CHAT") -> str:
        """
        Generates natural language response.
        Modified to handle new intent types and action-based data.
        """
        
        system_prompt = f"""You are a professional music catalog assistant for {self.company_identity}.

CORE RULES:
- Help customers explore our music catalog (albums, artists, tracks, genres)
- Be friendly, conversational, and enthusiastic about music
- NEVER mention: SQL, database, technical terms
- Always respond in Turkish

CRITICAL BOUNDARIES:
- You do NOT have access to customer data, employee information, or financial records
- If asked about these, politely explain you only handle music catalog queries
- You cannot see or access invoices, sales data, or personal information

TONE: Friendly music store assistant"""
        
        # Handle different context types
        if intent == "FORBIDDEN_DATA":
            user_prompt = f"""Customer asked: "{user_text}"

This request is for data you don't have access to (customer, employee, financial data).

Respond politely (Turkish):
- Explain you're a music catalog assistant
- You only have access to music information (albums, artists, tracks)
- Cannot access customer, employee, or financial data
- Offer to help with music-related queries instead

Keep it brief and friendly."""
        
        elif intent == "COMPANY_INFO":
            user_prompt = f"""Customer asked: "{user_text}"

Explain our music service (Turkish):
- Large music catalog with diverse genres
- Albums, tracks, artists from various genres
- Competitive pricing
- Easy browsing and discovery

Keep it engaging, 2-3 sentences."""
        
        elif intent == "OUT_OF_SCOPE":
            user_prompt = f"""Customer asked: "{user_text}"

This is outside your scope (not music-related).

Politely decline (Turkish):
- You're specialized in music catalog assistance
- Cannot help with this topic
- Offer to help find music instead

Stay friendly."""
        
        elif context == "NOT_AVAILABLE":
            user_prompt = f"""Customer asked: "{user_text}"

The requested data is not available in your music catalog scope.

Respond (Turkish):
- Inform them you couldn't find this in the music catalog
- Suggest alternative searches or browsing by genre
- Stay helpful and positive"""
        
        elif context and context != "NO_DATA":
            # This is actual music catalog data
            user_prompt = f"""Customer asked: "{user_text}"

Music catalog data retrieved:
{context}

Your task (Turkish):
1. Present this music information in a natural, conversational way
2. Include relevant details (artist, album, price, genre)
3. Format prices with ₺ or $ symbol
4. Be enthusiastic about the music
5. If showing multiple items, introduce them naturally

DO NOT mention: database, queries, technical terms
DO make it sound like recommendations from a music expert"""
        
        else:
            # Pure chat
            user_prompt = f"""Customer said: "{user_text}"

Respond naturally (Turkish):
- Answer warmly
- Show interest in their music preferences
- Keep it brief and conversational
- Ask what they'd like to explore"""
        
        try:
            final_resp = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=settings.RESPONSE_GENERATION_MODEL,
                temperature=settings.RESPONSE_TEMPERATURE
            )
            
            response = final_resp.choices[0].message.content
            cleaned_response = TextUtils.clean_text_for_tts(response)
            
            logger.info(f"{LogEmoji.CHAT} Response generated: {cleaned_response[:100]}...")
            return cleaned_response
        
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Response generation failed: {e}")
            return "Şu an cevap veremiyorum, lütfen biraz sonra tekrar deneyin."
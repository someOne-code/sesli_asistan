import re
from typing import Optional


class TextUtils:
    """Text processing utilities"""
    
    @staticmethod
    def extract_sql(text: str) -> str:
        """
        Extracts SQL query from LLM response.
        Handles markdown code blocks and extra text.
        """
        # Remove markdown code blocks
        text = re.sub(r'```sql\n?', '', text)
        text = re.sub(r'```\n?', '', text)
        
        # Find SQL query (starts with SELECT, INSERT, UPDATE, etc.)
        sql_pattern = r'(SELECT|INSERT|UPDATE|DELETE|WITH)\s+.*?(?=;|$)'
        match = re.search(sql_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            sql = match.group(0).strip()
            # Add semicolon if missing
            if not sql.endswith(';'):
                sql += ';'
            return sql
        
        # If no SQL pattern found, return cleaned text
        return text.strip()
    
    @staticmethod
    def clean_text_for_tts(text: str) -> str:
        """
        Cleans text for Text-to-Speech output.
        Removes special characters that might cause TTS issues.
        """
        # Remove markdown formatting
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)  # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)  # Code
        
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special TTS-breaking characters
        text = text.replace('|', '')
        text = text.replace('#', '')
        
        return text.strip()
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 200) -> str:
        """Truncates text to max_length with ellipsis"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + '...'
    
    @staticmethod
    def format_sql_results(results: list, limit: int = 5) -> str:
        """
        Formats SQL results into a readable string.
        Handles various result formats.
        """
        if not results:
            return "SONUC_YOK"
        
        # If results is already a string, return it
        if isinstance(results, str):
            return results
        
        # Truncate to limit
        results = results[:limit]
        
        # Format as list of dicts if possible
        formatted = []
        for item in results:
            if isinstance(item, dict):
                formatted.append(item)
            elif isinstance(item, (tuple, list)):
                formatted.append(dict(enumerate(item)))
            else:
                formatted.append(str(item))
        
        return str(formatted)
    
    @staticmethod
    def is_noise(text: str, noise_phrases: list, min_length: int = 3) -> bool:
        """
        Checks if input is likely noise/garbage.
        """
        if not text or len(text.strip()) < min_length:
            return True
        
        # Check against noise phrases
        text_lower = text.lower().strip()
        for phrase in noise_phrases:
            if text_lower == phrase.lower():
                return True
        
        # Check if mostly special characters
        special_char_ratio = sum(not c.isalnum() for c in text) / len(text)
        if special_char_ratio > 0.5:
            return True
        
        return False
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        Sanitizes user input to prevent injection attacks.
        """
        # Remove potential SQL injection patterns
        dangerous_patterns = [
            r';\s*DROP\s+',
            r';\s*DELETE\s+',
            r';\s*UPDATE\s+',
            r'--',
            r'/\*',
            r'\*/',
            r'xp_',
            r'sp_'
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()


class ValidationUtils:
    """Input validation utilities"""
    
    @staticmethod
    def is_valid_session_id(session_id: str) -> bool:
        """Validates session ID format"""
        # Allow alphanumeric, hyphens, underscores
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', session_id))
    
    @staticmethod
    def is_valid_sql(sql: str) -> bool:
        """Basic SQL query validation"""
        if not sql or len(sql) < 10:
            return False
        
        # Must start with SELECT
        if not sql.strip().upper().startswith('SELECT'):
            return False
        
        # Check for dangerous keywords
        dangerous = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE', 'CREATE']
        sql_upper = sql.upper()
        
        for keyword in dangerous:
            if keyword in sql_upper:
                return False
        
        return True
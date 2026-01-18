import re

class TextUtils:
    @staticmethod
    def extract_sql(text: str) -> str:
        """
        Extracts SQL code from a text response.
        Handles markdown code blocks and raw SQL statements.
        """
        # 1. Try to find sql code block
        match = re.search(r"```sql(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # 2. Try to find generic code block
        match_general = re.search(r"```(.*?)```", text, re.DOTALL)
        if match_general:
            return match_general.group(1).strip()
            
        # 3. Look for SELECT statements if no code blocks
        text_upper = text.upper()
        if "SELECT " in text_upper:
            # Simple heuristic: find first SELECT and take everything after
            # This is risky if there is explanation after, but better than nothing
            # A better approach might be to look for the end of the query (e.g. ;)
            start_index = text_upper.find("SELECT ")
            potential_sql = text[start_index:].strip()
            # Remove any trailing markdown or common ending text if possible
            # For now, we stick to the original logic but could improve it.
            return potential_sql
            
        return text.strip()

    @staticmethod
    def clean_text_for_tts(text: str) -> str:
        """
        Cleans text for Text-to-Speech engine.
        Removes emojis, markdown, and parenthetical expressions (actions).
        """
        # Remove parenthetical expressions like (güler) or (thinking)
        text = re.sub(r'\([^)]*\)', '', text)
        
        # Remove asterisks actions like *smiles*
        text = re.sub(r'\*[^*]*\*', '', text)
        
        # Remove common markdown symbols
        text = text.replace('"', '').replace("'", "")
        
        # Normalize whitespace
        text = " ".join(text.split())
        
        return text

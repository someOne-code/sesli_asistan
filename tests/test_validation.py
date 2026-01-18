
import pytest
import re

class ValidationUtils:
    @staticmethod
    def is_valid_session_id(session_id):
        if not session_id or not isinstance(session_id, str):
            return False
        if len(session_id) > 64: 
            return False
        # Allow alphanumeric, dashes, underscores
        return bool(re.match(r'^[a-zA-Z0-9_\-]+$', session_id))

    @staticmethod
    def sanitize_input(text):
        if not text: return ""
        # Remove common SQLi chars (basic sanitization)
        # Note: Real app uses SQLAlchemy param binding, so this is extra defense
        cleaned = text.replace(";", "").replace("--", "")
        return cleaned.strip()

@pytest.mark.parametrize("invalid_session_id", [
    "../../../etc/passwd",
    "<script>alert('xss')</script>",
    "'; DROP TABLE users; --",
    "a" * 100,  # Very long
    "",  # Empty
    None,
])
def test_session_id_validation(invalid_session_id):
    """Geçersiz session ID'ler reddedilmeli"""
    assert ValidationUtils.is_valid_session_id(invalid_session_id) == False

def test_valid_session_id():
    assert ValidationUtils.is_valid_session_id("user_123") == True
    assert ValidationUtils.is_valid_session_id("global-session") == True

@pytest.mark.parametrize("malicious_input, expected_part", [
    ("'; DELETE FROM Track", "DELETE FROM Track"),
    ("admin'--", "admin'"),
])
def test_input_sanitization(malicious_input, expected_part):
    """Zararlı inputlar temizlenmeli (Basic check)"""
    cleaned = ValidationUtils.sanitize_input(malicious_input)
    assert ';' not in cleaned
    assert '--' not in cleaned

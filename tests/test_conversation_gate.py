"""
Test suite for Conversation Gate (Behavioral, Language-Agnostic).
Tests behavior based on structural analysis and priority logic.
"""

import pytest
from app.core.services.conversation_gate import ConversationGate, GateDecision

@pytest.fixture
def gate():
    return ConversationGate()

# =========================================================================
# KEYWORD & PRIORITY TESTS
# =========================================================================

def test_greeting_is_social(gate):
    """
    Pure greetings are SOCIAL.
    """
    assert gate.evaluate("Selam") == GateDecision.SOCIAL
    assert gate.evaluate("Merhaba") == GateDecision.SOCIAL
    assert gate.evaluate("Günaydın") == GateDecision.SOCIAL

def test_business_keywords(gate):
    """
    Sentences with business keywords are BUSINESS.
    """
    # Music domain
    assert gate.evaluate("Metallica") == GateDecision.BUSINESS
    assert gate.evaluate("Fiyat ne") == GateDecision.BUSINESS
    assert gate.evaluate("Çal") == GateDecision.BUSINESS
    
    # Barber domain (New)
    assert gate.evaluate("Saç kesimi") == GateDecision.BUSINESS
    assert gate.evaluate("Sakal tıraşı") == GateDecision.BUSINESS
    assert gate.evaluate("Ne kadar?") == GateDecision.BUSINESS

def test_priority_inversion_greetings(gate):
    """
    CRITICAL: Greeting + Business -> BUSINESS.
    Business intent overrides social greeting.
    """
    assert gate.evaluate("Merhaba, saç kesimi ne kadar?") == GateDecision.BUSINESS
    assert gate.evaluate("Selam Metallica çal") == GateDecision.BUSINESS
    assert gate.evaluate("Günaydın randevu alabilir miyim?") == GateDecision.BUSINESS

def test_agent_focus_is_off_topic(gate):
    """
    Sentences asking about the Agent (2nd person) are OFF_TOPIC.
    """
    assert gate.evaluate("Senin adın ne?") == GateDecision.OFF_TOPIC
    assert gate.evaluate("En sevdiğin renk ne?") == GateDecision.OFF_TOPIC

def test_task_framing_is_business(gate):
    """
    User asking for permission to ask is preparing for BUSINESS.
    """
    assert gate.evaluate("Bir şey soracağım") == GateDecision.BUSINESS
    assert gate.evaluate("Bilgi alabilir miyim?") == GateDecision.BUSINESS

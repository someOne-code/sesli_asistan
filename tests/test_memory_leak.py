
import pytest
import psutil
import os

def test_memory_usage():
    """Verify memory usage logic works (requires psutil installed)."""
    process = psutil.Process(os.getpid())
    
    # 1. Read Memory
    mem_before = process.memory_info().rss
    assert mem_before > 0
    
    # 2. Do some dummy work
    data = {"key": "value" * 1000}
    
    # 3. Read Memory Again
    mem_after = process.memory_info().rss
    assert mem_after >= mem_before # Memory might grow slightly or stay same

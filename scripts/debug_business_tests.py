
import sys
import os
from unittest.mock import Mock

sys.path.append(os.getcwd())

from app.services.business_rules import MusicCatalogBusiness

def debug_business():
    print("Testing Business Rules...")
    
    mock_repo = Mock()
    business = MusicCatalogBusiness(mock_repo)

    # Test 1: Validation
    print("Test 1: Search Validation...", end="")
    res = business.search_tracks("a")
    if res["status"] == "error" and "2 karakter" in res["message"]:
        print("PASS")
    else:
        print(f"FAIL: {res}")
        return False

    # Test 2: Success
    print("Test 2: Search Success...", end="")
    mock_repo.search_tracks.return_value = [{"Name": "Test"}]
    res = business.search_tracks("Metallica")
    if res["status"] == "success" and len(res["data"]) == 1:
        print("PASS")
    else:
        print(f"FAIL: {res}")
        return False
        
    # Test 3: Budget
    print("Test 3: Budget Limit...", end="")
    res = business.get_budget_friendly_tracks(max_price=150.0)
    if res["status"] == "error":
        print("PASS")
    else:
        print(f"FAIL: {res}")
        return False

    print("ALL BUSINESS TESTS PASSED")
    return True

if __name__ == "__main__":
    if not debug_business():
        sys.exit(1)


"""
Unified System Verification Script.
Runs all Agile Test Suites (Unit, Security, Business, Integration, API, Benchmark)
and provides a consolidated report.
"""
import subprocess
import sys
import time
import os
import io

# Force UTF-8 for Windows Console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def run_suite(name, command):
    print(f"\n{'='*50}")
    print(f"[RUNNING]: {name}")
    print(f"{'='*50}")
    start = time.time()
    
    # Inject PYTHONPATH to include project root
    env = os.environ.copy()
    project_root = os.path.dirname(os.path.abspath(__file__))
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root};{current_pythonpath}"
    env["PYTHONIOENCODING"] = "utf-8"
    
    result = subprocess.run(command, shell=True, env=env)
    duration = time.time() - start
    
    status = "[PASS]" if result.returncode == 0 else "[FAIL]"
    print(f"\n>>> {status} | Duration: {duration:.2f}s")
    return result.returncode == 0

def main():
    print(f"*** STARTING SYSTEM VERIFICATION [Time: {time.ctime()}] ***")
    
    results = {}
    
    # 1. Unit Tests (Repository)
    results["Unit:Repo"] = run_suite("Repository Unit Tests", "python scripts/debug_repository_simple.py")
    
    # 2. Security Tests
    results["Unit:Security"] = run_suite("Security Tests", "python scripts/debug_security_simple.py")
    
    # 3. Business Layer
    results["Unit:Business"] = run_suite("Business Logic Tests", "python -m pytest tests/test_business.py")
    
    # 4. AI Manager (Mocked)
    results["Unit:AI"] = run_suite("AI Manager Tests", "python -m pytest tests/test_ai_manager_mock.py")
    
    # 5. Integration
    results["Integration"] = run_suite("Integration Tests", "python scripts/debug_integration_tests.py")
    
    # 6. API E2E
    results["API:E2E"] = run_suite("API End-to-End Tests", "python -m pytest tests/test_api_e2e.py")
    
    # 7. Benchmarks
    results["Performance"] = run_suite("Performance Benchmarks", "python scripts/debug_benchmark.py")
    
    # 8. Enhanced Reliability Tests
    # results["Reliability:Concurrency"] = run_suite("Concurrency Tests", "python -m pytest tests/test_concurrency.py")
    results["Reliability:ErrorRecovery"] = run_suite("Error Recovery Tests", "python -m pytest tests/test_error_recovery.py")
    results["Reliability:Validation"] = run_suite("Validation Tests", "python -m pytest tests/test_validation.py")
    results["Reliability:EdgeCases"] = run_suite("Edge Cases Tests", "python -m pytest tests/test_edge_cases.py")
    
    # 9. AI Partition Tests (Randomized Data Verification)
    results["AI:PartitionTests"] = run_suite("AI Partition Verification (Randomized)", "python scripts/auto_verify_ai.py")

    # 10. Rule-Based Normalizer Tests
    results["Unit:Normalizer"] = run_suite("Rule-Based Normalizer Tests", "python tests/test_normalizer.py")
    
    print(f"\n\n{'='*50}")
    print("--- CONSOLIDATED REPORT")
    print(f"{'='*50}")
    
    all_pass = True
    for suite, outcome in results.items():
        icon = "[PASS]" if outcome else "[FAIL]"
        print(f"{icon} {suite}")
        if not outcome:
            all_pass = False
            
    print(f"{'='*50}")
    if all_pass:
        print("SYSTEM READY FOR PRODUCTION")
        sys.exit(0)
    else:
        print("SYSTEM HAS FAILURES")
        sys.exit(1)

if __name__ == "__main__":
    main()

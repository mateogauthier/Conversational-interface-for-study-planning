"""Test script for Agent API endpoints."""

import requests
import json

# Agent API base URL
BASE_URL = "http://localhost:8002"

def test_health():
    """Test health endpoint."""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_root():
    """Test root endpoint."""
    print("\n=== Testing Root Endpoint ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_list_tools():
    """Test list tools endpoint."""
    print("\n=== Testing List Tools Endpoint ===")
    response = requests.get(f"{BASE_URL}/tools/list")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Tool Count: {data.get('tool_count', 0)}")
    print("Available Tools:")
    for tool in data.get('tools', []):
        print(f"  - {tool['name']}: {tool['description']}")
    return response.status_code == 200

def test_search_documents():
    """Test search documents endpoint (requires valid user data)."""
    print("\n=== Testing Search Documents Endpoint ===")

    # Example request - replace with actual user data
    payload = {
        "query": "test query",
        "n_results": 5,
        "user_id": "test_user_id",
        "user_auth0_id": "test_auth0_id",
        "user_role": "student"
    }

    response = requests.post(
        f"{BASE_URL}/tools/search_documents",
        json=payload
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Chunks Found: {data.get('n_chunks_found', 0)}")
    else:
        print(f"Error: {response.text}")

    return response.status_code == 200

def main():
    """Run all tests."""
    print("=" * 60)
    print("Agent API Test Suite")
    print("=" * 60)

    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("List Tools", test_list_tools),
        # ("Search Documents", test_search_documents),  # Uncomment when DB is ready
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()

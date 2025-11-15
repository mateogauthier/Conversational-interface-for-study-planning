"""
Test concurrent request handling to verify async implementation.

This test validates that the API can handle multiple requests concurrently
without blocking, which was the main issue with the synchronous implementation.
"""

import asyncio
import time
import httpx
from typing import List, Dict, Any


async def make_request(client: httpx.AsyncClient, url: str, payload: Dict[str, Any], request_id: int) -> Dict[str, Any]:
    """Make a single async request and track timing."""
    start_time = time.time()
    try:
        response = await client.post(url, json=payload, timeout=30.0)
        end_time = time.time()
        duration = end_time - start_time

        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "duration": duration,
            "success": response.status_code == 200,
            "start_time": start_time,
            "end_time": end_time
        }
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        return {
            "request_id": request_id,
            "status_code": 0,
            "duration": duration,
            "success": False,
            "error": str(e),
            "start_time": start_time,
            "end_time": end_time
        }


async def test_concurrent_requests(base_url: str = "http://localhost:8000", num_requests: int = 5):
    """
    Test concurrent request handling.

    Args:
        base_url: Base URL of the API
        num_requests: Number of concurrent requests to make
    """
    print(f"\n{'='*80}")
    print(f"CONCURRENT REQUEST TEST")
    print(f"{'='*80}")
    print(f"Base URL: {base_url}")
    print(f"Number of concurrent requests: {num_requests}")
    print(f"{'='*80}\n")

    # Test endpoint - using a simple LLM query
    # Note: In a real test, you would need authentication tokens
    # This is a simplified version for demonstration
    endpoint = f"{base_url}/llm/query"

    payload = {
        "prompt": "What is 2+2?",
        "model": None  # Use default model
    }

    # Create async HTTP client
    async with httpx.AsyncClient() as client:
        # Launch all requests concurrently
        print(f"Launching {num_requests} concurrent requests at {time.strftime('%H:%M:%S')}...")
        overall_start = time.time()

        tasks = [
            make_request(client, endpoint, payload, i+1)
            for i in range(num_requests)
        ]

        # Wait for all requests to complete
        results = await asyncio.gather(*tasks)

        overall_end = time.time()
        overall_duration = overall_end - overall_start

        # Analyze results
        print(f"\n{'='*80}")
        print(f"RESULTS")
        print(f"{'='*80}\n")

        successful = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])

        print(f"Total requests: {num_requests}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Overall duration: {overall_duration:.2f}s")
        print(f"\nIndividual request timings:")
        print(f"{'Request':<10} {'Status':<10} {'Duration (s)':<15} {'Result'}")
        print(f"{'-'*80}")

        for result in results:
            status = "✓ OK" if result["success"] else "✗ FAIL"
            req_id = f"#{result['request_id']}"
            duration = f"{result['duration']:.2f}s"
            status_code = result.get("status_code", 0)
            error = result.get("error", "")

            if result["success"]:
                print(f"{req_id:<10} {status:<10} {duration:<15} HTTP {status_code}")
            else:
                print(f"{req_id:<10} {status:<10} {duration:<15} {error[:40]}")

        # Calculate parallelism metrics
        print(f"\n{'='*80}")
        print(f"PARALLELISM ANALYSIS")
        print(f"{'='*80}\n")

        # Sort by start time to see execution overlap
        sorted_results = sorted(results, key=lambda x: x["start_time"])

        # Calculate if requests actually ran in parallel
        # If they ran sequentially, total time would be sum of all durations
        # If they ran in parallel, total time would be ~max(durations)
        total_sequential_time = sum(r["duration"] for r in results)
        max_single_duration = max(r["duration"] for r in results)

        parallelism_factor = total_sequential_time / overall_duration if overall_duration > 0 else 0

        print(f"If requests ran sequentially: {total_sequential_time:.2f}s")
        print(f"Actual overall duration: {overall_duration:.2f}s")
        print(f"Parallelism factor: {parallelism_factor:.2f}x")
        print(f"Expected for perfect parallel: {num_requests:.2f}x")

        if parallelism_factor > 1.5:
            print(f"\n✓ SUCCESS: Requests are running concurrently!")
            print(f"  The API is handling multiple requests in parallel.")
        else:
            print(f"\n✗ WARNING: Requests may be blocking!")
            print(f"  Expected parallelism factor > 1.5, got {parallelism_factor:.2f}")
            print(f"  This suggests requests are being processed sequentially.")

        # Timeline visualization
        print(f"\n{'='*80}")
        print(f"REQUEST TIMELINE")
        print(f"{'='*80}\n")

        min_start = min(r["start_time"] for r in results)
        scale = 2  # characters per second

        for result in sorted_results:
            req_id = f"Request #{result['request_id']}"
            offset_start = int((result["start_time"] - min_start) * scale)
            duration_chars = max(1, int(result["duration"] * scale))

            timeline = " " * offset_start + "█" * duration_chars
            status = "✓" if result["success"] else "✗"

            print(f"{req_id:<15} {status} |{timeline}")

        print(f"\nScale: Each █ ≈ {1/scale:.1f}s")
        print(f"\nIf bars overlap horizontally, requests ran concurrently.")
        print(f"If bars are one after another, requests ran sequentially.\n")

        return {
            "total_requests": num_requests,
            "successful": successful,
            "failed": failed,
            "overall_duration": overall_duration,
            "parallelism_factor": parallelism_factor,
            "results": results
        }


async def test_concurrent_rag_queries(
    base_url: str = "http://localhost:8000",
    token: str = None,
    num_requests: int = 3
):
    """
    Test concurrent RAG queries (requires authentication).

    Args:
        base_url: Base URL of the API
        token: Authentication token
        num_requests: Number of concurrent requests
    """
    if not token:
        print("\n⚠ WARNING: No authentication token provided.")
        print("  To test authenticated endpoints, provide a token:")
        print("  python tests/test_concurrent.py --token YOUR_TOKEN\n")
        return

    print(f"\n{'='*80}")
    print(f"CONCURRENT RAG QUERY TEST (Authenticated)")
    print(f"{'='*80}\n")

    endpoint = f"{base_url}/rag/search"
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "prompt": "test query",
        "n_results": 3,
        "use_llm": True
    }

    async with httpx.AsyncClient() as client:
        print(f"Launching {num_requests} concurrent RAG queries...")
        overall_start = time.time()

        tasks = []
        for i in range(num_requests):
            # Add headers to the request
            async def make_auth_request(req_id):
                start = time.time()
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                        timeout=60.0
                    )
                    end = time.time()
                    return {
                        "request_id": req_id,
                        "status_code": response.status_code,
                        "duration": end - start,
                        "success": response.status_code == 200
                    }
                except Exception as e:
                    end = time.time()
                    return {
                        "request_id": req_id,
                        "status_code": 0,
                        "duration": end - start,
                        "success": False,
                        "error": str(e)
                    }

            tasks.append(make_auth_request(i+1))

        results = await asyncio.gather(*tasks)
        overall_duration = time.time() - overall_start

        successful = sum(1 for r in results if r["success"])

        print(f"\nResults: {successful}/{num_requests} successful")
        print(f"Overall duration: {overall_duration:.2f}s")

        total_duration = sum(r["duration"] for r in results)
        parallelism = total_duration / overall_duration if overall_duration > 0 else 0

        print(f"Parallelism factor: {parallelism:.2f}x")

        if parallelism > 1.5:
            print("✓ RAG queries are running concurrently!")
        else:
            print("✗ RAG queries appear to be blocking!")


if __name__ == "__main__":
    import sys

    # Parse command line arguments
    base_url = "http://localhost:8000"
    num_requests = 5
    token = None

    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--url":
            base_url = sys.argv[i+2]
        elif arg == "--requests":
            num_requests = int(sys.argv[i+2])
        elif arg == "--token":
            token = sys.argv[i+2]

    print("\n" + "="*80)
    print("ASYNC CONCURRENCY TEST SUITE")
    print("="*80)
    print("\nThis test validates that the API handles concurrent requests properly.")
    print("The async refactoring should allow multiple requests to be processed")
    print("simultaneously without blocking.\n")

    # Run basic concurrent test
    result = asyncio.run(test_concurrent_requests(base_url, num_requests))

    # If token provided, also test authenticated endpoints
    if token:
        asyncio.run(test_concurrent_rag_queries(base_url, token, min(3, num_requests)))

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")

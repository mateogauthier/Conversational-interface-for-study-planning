"""Test script for web search functionality."""

import asyncio
from duckduckgo_search import DDGS


async def test_web_search():
    """Test DuckDuckGo web search."""
    query = "Python programming language"
    max_results = 3

    print(f"\n{'='*60}")
    print(f"Testing DuckDuckGo Web Search")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Max Results: {max_results}\n")

    try:
        # Perform search
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results))

        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", ""),
            })

        print(f"✅ Search completed successfully!")
        print(f"Found {len(formatted_results)} results\n")

        # Display results
        for i, result in enumerate(formatted_results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"Snippet: {result['snippet'][:150]}...")

        return {
            "query": query,
            "results": formatted_results,
            "result_count": len(formatted_results)
        }

    except Exception as e:
        print(f"\n❌ Error during web search: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_web_search())

#!/usr/bin/env python3
"""Test script to verify artifact extraction is working."""

import re
from typing import List, Dict, Any, Tuple

def extract_artifacts(response_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extract artifacts from LLM response text.

    Returns:
        Tuple of (clean_text_without_artifacts, list_of_artifacts)
    """
    artifacts = []

    # Pattern to match <artifact> tags with attributes
    pattern = r'<artifact\s+([^>]+)>(.*?)</artifact>'

    def extract_artifact(match):
        # Parse attributes
        attrs_str = match.group(1)
        content = match.group(2).strip()

        # Extract attributes
        attr_pattern = r'(\w+)="([^"]*)"'
        attrs = dict(re.findall(attr_pattern, attrs_str))

        artifact = {
            "type": attrs.get("type", "code"),
            "language": attrs.get("language"),
            "title": attrs.get("title"),
            "content": content
        }

        artifacts.append(artifact)

        # Return a placeholder
        return f"\n[Artifact: {artifact.get('title', artifact['type'])}]\n"

    # Remove artifacts from response and collect them
    clean_text = re.sub(pattern, extract_artifact, response_text, flags=re.DOTALL)

    # Clean up excessive newlines
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()

    print(f"Extracted {len(artifacts)} artifact(s) from response")

    return clean_text, artifacts


# Test cases
test_response_1 = """Here's a diagram showing the library book request process:

<artifact type="mermaid" title="Library Book Request Process">
graph LR
    A[User] --> B[Request Book]
    B --> C[Check Availability]
    C --> D[Available]
    C --> E[Not Available]
    D --> F[Loan Book]
    E --> G[Notify User]
</artifact>

This diagram shows the main steps in the process.
"""

test_response_2 = """Here's a Python example:

<artifact type="code" language="python" title="Fibonacci Function">
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
</artifact>

This is a simple recursive implementation.
"""

test_response_3 = """No artifacts in this response, just plain text."""

print("=" * 60)
print("Test 1: Mermaid Diagram Artifact")
print("=" * 60)
clean, artifacts = extract_artifacts(test_response_1)
print(f"\nClean text:\n{clean}")
print(f"\nArtifacts: {artifacts}")

print("\n" + "=" * 60)
print("Test 2: Code Artifact")
print("=" * 60)
clean, artifacts = extract_artifacts(test_response_2)
print(f"\nClean text:\n{clean}")
print(f"\nArtifacts: {artifacts}")

print("\n" + "=" * 60)
print("Test 3: No Artifacts")
print("=" * 60)
clean, artifacts = extract_artifacts(test_response_3)
print(f"\nClean text:\n{clean}")
print(f"\nArtifacts: {artifacts}")

print("\n" + "=" * 60)
print("✅ All tests completed!")
print("=" * 60)

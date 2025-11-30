#!/usr/bin/env python3
"""Test Instructor integration with Ollama."""

import asyncio
from app.services.llm_service import LLMService

async def test_instructor():
    """Test that Instructor client initializes correctly."""

    llm_service = LLMService()

    print("=" * 80)
    print("INSTRUCTOR CLIENT TEST")
    print("=" * 80)

    try:
        # Get Instructor client
        client = llm_service._get_instructor_client()
        print("✅ Instructor client created successfully")
        print(f"Client type: {type(client)}")
        print(f"Has chat: {hasattr(client, 'chat')}")
        print(f"Has completions: {hasattr(client.chat, 'completions') if hasattr(client, 'chat') else False}")

        # Test a simple structured output
        print("\n" + "=" * 80)
        print("Testing structured output generation...")
        print("=" * 80)

        from app.models.llm_responses import StructuredLLMResponse

        try:
            response = await client.chat.completions.create(
                model="llama2:latest",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that generates structured responses with artifacts."
                    },
                    {
                        "role": "user",
                        "content": "Create a simple example table with 2 rows showing student names and grades."
                    }
                ],
                response_model=StructuredLLMResponse,
            )

            print(f"\n✅ Structured response generated successfully!")
            print(f"\nText: {response.text[:100]}...")
            print(f"Number of artifacts: {len(response.artifacts)}")

            for i, artifact in enumerate(response.artifacts):
                print(f"\nArtifact {i+1}:")
                print(f"  Type: {artifact.type}")
                print(f"  Title: {artifact.title}")
                print(f"  Content length: {len(artifact.content)} chars")

            print("\n" + "=" * 80)
            print("✅ ALL TESTS PASSED - Instructor is working correctly!")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ ERROR generating structured output: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ ERROR creating Instructor client: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_instructor())

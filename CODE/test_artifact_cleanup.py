#!/usr/bin/env python3
"""Test that artifacts are properly extracted from text and don't appear in chat."""

import asyncio
from app.services.llm_service import LLMService


async def test_artifact_cleanup():
    """Test that HTML tables are removed from text when present in both text and artifacts."""

    llm_service = LLMService()

    print("=" * 80)
    print("ARTIFACT CLEANUP TEST")
    print("=" * 80)
    print()

    # Simulate a response where LLM puts table in both text and artifacts
    # This is what was happening in production
    test_text_with_table = """Aquí están las materias que has aprobado:

<table><thead><tr><th>Materia</th><th>Resultado</th></tr></thead><tbody><tr><td>Base de Datos 1</td><td>Aprobada</td></tr><tr><td>Programación 1</td><td>Aprobada</td></tr></tbody></table>

Como puedes ver, has aprobado 2 materias."""

    print("📝 Original text with embedded table:")
    print(test_text_with_table)
    print()

    # Extract artifacts (this is what the fix does)
    clean_text, extracted_artifacts = llm_service._extract_artifacts(test_text_with_table)

    print("-" * 80)
    print("✅ AFTER CLEANUP:")
    print("-" * 80)
    print()
    print("📄 Clean text (should NOT contain <table> tags):")
    print(clean_text)
    print()
    print(f"🎨 Extracted {len(extracted_artifacts)} artifact(s):")
    for i, artifact in enumerate(extracted_artifacts):
        print(f"\nArtifact {i+1}:")
        print(f"  Type: {artifact['type']}")
        print(f"  Title: {artifact['title']}")
        print(f"  Content preview: {artifact['content'][:100]}...")
    print()

    # Verify cleanup worked
    if "<table>" in clean_text or "<thead>" in clean_text:
        print("❌ FAIL: Table HTML still present in text!")
        return False
    elif len(extracted_artifacts) == 0:
        print("❌ FAIL: No artifacts extracted!")
        return False
    elif extracted_artifacts[0]['type'] != 'html':
        print("❌ FAIL: Artifact type is not 'html'!")
        return False
    else:
        print("✅ SUCCESS: Table removed from text and extracted as artifact!")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_artifact_cleanup())
    exit(0 if success else 1)

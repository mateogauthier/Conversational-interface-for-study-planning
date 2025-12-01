#!/usr/bin/env python3
"""Test markdown table extraction."""

from app.services.llm_service import LLMService

def test_markdown_table_extraction():
    """Test that markdown tables are correctly extracted as artifacts."""

    llm_service = LLMService()

    # Sample response with markdown table (like the one from your query)
    response_text = """¡Claro! A continuación, te presento la tabla con tus materias aprobadas y la nota más alta:

| Materias | Fecha | Resultado | Nota |
| --- | --- | --- | --- |
| Comunicación y liderazgo (y negociación) | 23/03/2023 | Aprobada | 96% |
| Análisis y diseño funcional | 09/02/2023 | Aprobada | 70% |
| Diseño de aplicaciones 2 | 07/12/2023 | Aprobada | 79% |
| Métodos cuantitativos para los negocios | 14/07/2022 | Aprobada | 86% |
| Redes | 10/07/2023 | Aprobada | 86% |
| Taller de seguridad informática | 29/08/2024 | Aprobada | 75% |
| Bases de datos 3 | 06/12/2023 | Aprobada | 86% |
| Ingeniería de software ágil 1 | 03/07/2024 | Aprobada | 72% |

La nota más alta es del 96% obtenida en la materia de Comunicación y liderazgo (y negociación)."""

    # Extract artifacts
    clean_text, artifacts = llm_service._extract_artifacts(response_text)

    print("=" * 80)
    print("MARKDOWN TABLE EXTRACTION TEST")
    print("=" * 80)
    print(f"\nNumber of artifacts extracted: {len(artifacts)}")
    print(f"\nClean text (without table):\n{clean_text}")

    if artifacts:
        print(f"\n{'=' * 80}")
        print("EXTRACTED ARTIFACTS:")
        print("=" * 80)
        for i, artifact in enumerate(artifacts):
            print(f"\nArtifact {i + 1}:")
            print(f"  Type: {artifact['type']}")
            print(f"  Title: {artifact['title']}")
            print(f"  Content length: {len(artifact['content'])} chars")
            print(f"\nContent preview (first 500 chars):")
            print(artifact['content'][:500])
    else:
        print("\n❌ ERROR: No artifacts were extracted!")
        print("The markdown table should have been detected and converted to an HTML artifact.")

    print("\n" + "=" * 80)

    # Check if table was successfully extracted
    assert len(artifacts) == 1, f"Expected 1 artifact, got {len(artifacts)}"
    assert artifacts[0]['type'] == 'html', f"Expected type 'html', got '{artifacts[0]['type']}'"
    assert '<table' in artifacts[0]['content'], "Artifact should contain HTML table"
    assert 'Comunicación y liderazgo' in artifacts[0]['content'], "Table should contain subject names"
    assert '96%' in artifacts[0]['content'], "Table should contain grades"

    print("✅ All tests passed!")
    print("The markdown table was successfully detected and converted to an HTML artifact.")
    print("=" * 80)

if __name__ == "__main__":
    test_markdown_table_extraction()

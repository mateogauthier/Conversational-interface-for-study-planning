#!/usr/bin/env python3
"""Test adaptive RAG routing system."""

import asyncio
from app.services.routing_service import routing_service, RoutingStrategy


async def test_routing():
    """Test routing classification with various query types."""

    test_cases = [
        # NO_RETRIEVAL cases (should skip ChromaDB)
        ("hello", RoutingStrategy.NO_RETRIEVAL),
        ("hi there", RoutingStrategy.NO_RETRIEVAL),
        ("hola", RoutingStrategy.NO_RETRIEVAL),
        ("buenos días", RoutingStrategy.NO_RETRIEVAL),
        ("how are you", RoutingStrategy.NO_RETRIEVAL),

        # SINGLE_RETRIEVAL cases (standard RAG)
        ("¿cuáles son los requisitos para bases de datos 3?", RoutingStrategy.SINGLE_RETRIEVAL),
        ("muéstrame mis notas", RoutingStrategy.SINGLE_RETRIEVAL),
        ("what is the enrollment calendar", RoutingStrategy.SINGLE_RETRIEVAL),
        ("cuándo es el período de inscripción", RoutingStrategy.SINGLE_RETRIEVAL),
        ("qué materias aprobé", RoutingStrategy.SINGLE_RETRIEVAL),
        ("show my academic record", RoutingStrategy.SINGLE_RETRIEVAL),

        # MULTI_RETRIEVAL cases (complex queries)
        ("compara todas mis materias de programación", RoutingStrategy.MULTI_RETRIEVAL),
        ("crea un plan de estudios para el próximo semestre", RoutingStrategy.MULTI_RETRIEVAL),
        ("analiza mi progreso académico y recomienda materias", RoutingStrategy.MULTI_RETRIEVAL),
        ("compare database 1 and database 2 requirements", RoutingStrategy.MULTI_RETRIEVAL),
    ]

    print("=" * 80)
    print("ADAPTIVE RAG ROUTING TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for query, expected_strategy in test_cases:
        result = await routing_service.classify_query(
            query=query,
            mode="hybrid",
            confidence_threshold=0.7
        )

        actual_strategy = result['strategy']
        confidence = result['confidence']
        method = result['method']
        reasoning = result['reasoning']

        match = actual_strategy == expected_strategy
        status = "✅ PASS" if match else "❌ FAIL"

        if match:
            passed += 1
        else:
            failed += 1

        print(f"{status}")
        print(f"  Query: \"{query}\"")
        print(f"  Expected: {expected_strategy}")
        print(f"  Actual: {actual_strategy} (confidence: {confidence:.2f}, method: {method})")
        print(f"  Reasoning: {reasoning}")
        print()

    print("=" * 80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} total")
    print("=" * 80)

    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed - review routing logic")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_routing())
    exit(0 if success else 1)

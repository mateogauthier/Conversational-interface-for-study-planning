"""Query routing service for adaptive RAG.

This service determines whether a query needs document retrieval (RAG),
can be answered directly, or requires multi-step reasoning.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategies for query handling."""
    NO_RETRIEVAL = "no_retrieval"  # Answer directly without documents
    SINGLE_RETRIEVAL = "single_retrieval"  # Standard RAG with one search
    MULTI_RETRIEVAL = "multi_retrieval"  # Complex queries needing multiple searches


class RoutingService:
    """Service for intelligent query routing in adaptive RAG."""

    def __init__(self):
        """Initialize the routing service."""
        self.llm_service = None  # Lazy loaded to avoid circular imports

    def _get_llm_service(self):
        """Lazy load LLM service to avoid circular imports."""
        if self.llm_service is None:
            from app.services.llm_service import llm_service
            self.llm_service = llm_service
        return self.llm_service

    async def classify_query(
        self,
        query: str,
        mode: str = "hybrid",
        confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Classify a query to determine routing strategy.

        Args:
            query: The user's query text
            mode: Routing mode - 'heuristic', 'llm', or 'hybrid'
            confidence_threshold: Minimum confidence to use heuristic classification

        Returns:
            Dictionary with:
                - strategy: RoutingStrategy enum value
                - confidence: Float confidence score (0.0-1.0)
                - reasoning: String explanation of classification
                - method: Which method was used ('heuristic' or 'llm')
        """
        logger.info(f"Classifying query with mode: {mode}")

        if mode == "heuristic":
            return self._heuristic_classify(query)
        elif mode == "llm":
            return await self._llm_classify(query)
        else:  # hybrid
            # Try heuristics first for speed
            heuristic_result = self._heuristic_classify(query)

            # If high confidence, use heuristic result
            if heuristic_result["confidence"] >= confidence_threshold:
                logger.info(f"Using heuristic classification with {heuristic_result['confidence']} confidence")
                return heuristic_result

            # Otherwise, use LLM for better accuracy
            logger.info(f"Heuristic confidence {heuristic_result['confidence']} below threshold, using LLM")
            return await self._llm_classify(query)

    def _heuristic_classify(self, query: str) -> Dict[str, Any]:
        """
        Fast heuristic-based classification.

        Args:
            query: The user's query text

        Returns:
            Classification result with strategy, confidence, and reasoning
        """
        query_lower = query.lower().strip()

        # Category 1: Greetings and simple conversational queries (NO RETRIEVAL)
        greetings = [
            'hello', 'hi', 'hey', 'hola', 'buenos días', 'buenas tardes',
            'buenas noches', 'good morning', 'good afternoon', 'good evening',
            'howdy', 'saludos', 'qué tal', 'how are you', 'cómo estás'
        ]

        if any(greeting in query_lower for greeting in greetings) and len(query.split()) <= 5:
            return {
                "strategy": RoutingStrategy.NO_RETRIEVAL,
                "confidence": 0.95,
                "reasoning": "Simple greeting detected - no document retrieval needed",
                "method": "heuristic"
            }

        # Category 2: Academic queries MUST be checked BEFORE simple factual questions
        # to avoid false negatives
        academic_strong_keywords = [
            # Course-related
            'materia', 'materias', 'curso', 'cursos', 'asignatura',
            'subject', 'course', 'class',
            # Program-related
            'programa', 'plan de estudios', 'curriculum', 'carrera',
            'degree', 'major', 'pensum',
            # Requirements
            'requisito', 'requisitos', 'prerequisito', 'requirement',
            'prerrequisite', 'corequisite',
            # Regulations
            'reglamento', 'normativa', 'política', 'regulation',
            'policy', 'rule',
            # Academic records
            'nota', 'notas', 'calificación', 'grade', 'grades',
            'promedio', 'average', 'gpa',
            # Registration
            'inscripción', 'matrícula', 'registration', 'enrollment',
            'calendario', 'calendar', 'horario', 'schedule'
        ]

        # Check for academic keywords FIRST
        has_academic_keywords = any(keyword in query_lower for keyword in academic_strong_keywords)

        # Category 2b: Simple factual questions (NO RETRIEVAL) - but only if NO academic keywords
        simple_patterns = [
            'what is', 'qué es', 'cuánto es', 'how much', 'define',
            'what does', 'qué significa', 'who is', 'quién es'
        ]

        # Only no-retrieval if very short, clearly general knowledge, AND no academic keywords
        if (any(pattern in query_lower for pattern in simple_patterns) and
            len(query.split()) <= 8 and
            not has_academic_keywords):
            return {
                "strategy": RoutingStrategy.NO_RETRIEVAL,
                "confidence": 0.80,
                "reasoning": "Simple factual question without academic context",
                "method": "heuristic"
            }

        # Category 3: Complex reasoning queries (MULTI RETRIEVAL) - check BEFORE academic
        # to capture complex academic queries
        complexity_indicators = [
            # Comparison
            'comparar', 'compare', 'compara', 'diferencia entre', 'difference between',
            'versus', 'vs', 'mejor que', 'better than', 'peor que', 'worse than',
            # Analysis
            'analizar', 'analyze', 'analiza', 'evaluar', 'evaluate', 'evalúa',
            'explicar', 'explain', 'explica',
            'por qué', 'why', 'cómo funciona', 'how does', 'how work',
            # Planning
            'plan', 'planificar', 'planifica', 'crea un plan', 'create a plan',
            'estrategia', 'strategy', 'recomendar', 'recomienda',
            'recommend', 'sugerir', 'suggest', 'sugiere', 'aconsejar', 'advise',
            # Multiple entities
            'todos los', 'todas las', 'all the', 'all my', 'todas mis', 'todos mis',
            'cuáles son', 'which are', 'lista de', 'list of',
            'mostrar todas', 'mostrar todos', 'show all'
        ]

        has_complexity = any(indicator in query_lower for indicator in complexity_indicators)

        # If both complex AND academic, it's multi-retrieval
        if has_complexity and has_academic_keywords:
            return {
                "strategy": RoutingStrategy.MULTI_RETRIEVAL,
                "confidence": 0.85,
                "reasoning": "Complex academic query requiring multi-document reasoning",
                "method": "heuristic"
            }

        # Category 4: Academic queries (SINGLE RETRIEVAL - high confidence)
        if has_academic_keywords:
            return {
                "strategy": RoutingStrategy.SINGLE_RETRIEVAL,
                "confidence": 0.90,
                "reasoning": "Academic keywords detected - document retrieval needed",
                "method": "heuristic"
            }

        # Category 5: Uncertain - medium confidence, default to safe option
        # If query is long and unclear, assume it needs retrieval
        if len(query.split()) > 10:
            return {
                "strategy": RoutingStrategy.SINGLE_RETRIEVAL,
                "confidence": 0.60,
                "reasoning": "Long query with uncertain intent - defaulting to retrieval",
                "method": "heuristic"
            }

        # Default fallback: short, unclear queries
        return {
            "strategy": RoutingStrategy.SINGLE_RETRIEVAL,
            "confidence": 0.50,
            "reasoning": "Uncertain query type - defaulting to safe retrieval option",
            "method": "heuristic"
        }

    async def _llm_classify(self, query: str) -> Dict[str, Any]:
        """
        LLM-based classification for more nuanced understanding.

        Args:
            query: The user's query text

        Returns:
            Classification result with strategy, confidence, and reasoning
        """
        llm_service = self._get_llm_service()

        # Create classification prompt
        classifier_prompt = f"""Classify this user query into ONE of these categories:

1. NO_RETRIEVAL: Simple greetings, basic math, general knowledge that doesn't need university documents
   Examples: "hello", "what is 2+2", "who is Albert Einstein"

2. SINGLE_RETRIEVAL: Questions that need to look up information from university documents
   Examples: "what are the prerequisites for Database course", "when is enrollment period", "show my grades"

3. MULTI_RETRIEVAL: Complex questions needing multiple documents or deep reasoning
   Examples: "compare all my programming courses", "create a study plan for next semester", "what courses should I take to improve my GPA"

User query: "{query}"

Respond with ONLY the category name (NO_RETRIEVAL, SINGLE_RETRIEVAL, or MULTI_RETRIEVAL) and a brief reason.
Format: CATEGORY | reason"""

        try:
            # Use a quick LLM call for classification
            response = await llm_service.generate_response(
                prompt=classifier_prompt,
                model=None  # Use default model
            )

            response_text = response.get("response", "").strip()

            # Parse response
            if "|" in response_text:
                category_str, reasoning = response_text.split("|", 1)
                category_str = category_str.strip().upper()
                reasoning = reasoning.strip()
            else:
                category_str = response_text.upper()
                reasoning = "LLM classification"

            # Map to strategy
            if "NO_RETRIEVAL" in category_str:
                strategy = RoutingStrategy.NO_RETRIEVAL
                confidence = 0.85
            elif "MULTI_RETRIEVAL" in category_str:
                strategy = RoutingStrategy.MULTI_RETRIEVAL
                confidence = 0.80
            else:  # SINGLE_RETRIEVAL or unclear
                strategy = RoutingStrategy.SINGLE_RETRIEVAL
                confidence = 0.75

            return {
                "strategy": strategy,
                "confidence": confidence,
                "reasoning": reasoning,
                "method": "llm"
            }

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Fallback to safe default
            return {
                "strategy": RoutingStrategy.SINGLE_RETRIEVAL,
                "confidence": 0.50,
                "reasoning": f"LLM classification failed, using safe default. Error: {str(e)}",
                "method": "llm_fallback"
            }


# Global routing service instance
routing_service = RoutingService()

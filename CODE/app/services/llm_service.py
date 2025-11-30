"""LLM service for Ollama integration."""

import json
import logging
import httpx
import re
from typing import Optional, Dict, Any, List, Tuple

import instructor
from ollama import AsyncClient

from app.core.config import get_settings
from app.core.exceptions import LLMException, LLMNotAvailableHTTPException
from app.models.llm_responses import StructuredLLMResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """Service for LLM operations using Ollama."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._instructor_client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _get_instructor_client(self):
        """Get or create Instructor client for structured outputs."""
        if self._instructor_client is None:
            # Create Ollama async client
            from openai import AsyncOpenAI

            # Ollama has OpenAI-compatible API
            ollama_client = AsyncOpenAI(
                base_url=f"{self.base_url}/v1",
                api_key="ollama",  # Ollama doesn't require a real API key
            )
            # Wrap with Instructor using JSON mode (more compatible than tool calling)
            self._instructor_client = instructor.patch(
                ollama_client,
                mode=instructor.Mode.JSON
            )
        return self._instructor_client

    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except (httpx.RequestError, httpx.HTTPError, Exception):
            return False

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return data.get("models", [])

        except (httpx.RequestError, httpx.HTTPError) as e:
            logger.error(f"Error getting models: {str(e)}")
            raise LLMNotAvailableHTTPException(f"Cannot connect to Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting models: {str(e)}")
            raise LLMException(f"Error getting models: {str(e)}")

    async def model_exists(self, model: str) -> bool:
        """Check if a specific model exists."""
        try:
            models = await self.get_available_models()
            return any(m.get("name", "").startswith(model) for m in models)
        except Exception:
            return False

    async def ensure_model(self, model: str) -> bool:
        """Ensure a model is available, pull if necessary."""
        try:
            if await self.model_exists(model):
                return True

            logger.info(f"Model {model} not found, attempting to pull...")
            pull_url = f"{self.base_url}/api/pull"

            client = await self._get_client()
            response = await client.post(
                pull_url,
                json={"name": model},
                timeout=300  # 5 minutes for model pulling
            )

            if response.status_code == 200:
                logger.info(f"Successfully pulled model {model}")
                return True
            else:
                logger.error(f"Failed to pull model {model}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error ensuring model {model}: {str(e)}")
            return False

    async def generate_response(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response using Ollama."""
        if not await self.is_available():
            raise LLMNotAvailableHTTPException("Ollama service is not available")

        model = model or self.default_model

        try:
            # Ensure model is available
            if not await self.ensure_model(model):
                logger.warning(f"Model {model} not available, falling back to {self.default_model}")
                model = self.default_model
                if not await self.ensure_model(model):
                    raise LLMException(f"Default model {self.default_model} is not available")

            # Generate response
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False  # Use non-streaming for more reliable response
            }

            client = await self._get_client()
            response = await client.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            # Process non-streaming response
            result = response.json()
            answer = result.get("response", "")

            if not answer.strip():
                raise LLMException("Empty response received from LLM")

            return {
                "response": answer,
                "model_used": model
            }

        except (httpx.RequestError, httpx.HTTPError) as e:
            logger.error(f"Error querying Ollama: {str(e)}")
            raise LLMNotAvailableHTTPException(f"Cannot connect to Ollama: {str(e)}")
        except LLMException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM query: {str(e)}")
            raise LLMException(f"Error generating response: {str(e)}")

    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        instructions: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        enable_artifacts: bool = True
    ) -> Dict[str, Any]:
        """Generate a response with provided context and optional conversation history using Instructor."""
        from app.core.config import get_settings
        settings = get_settings()

        # Truncate context if too long to prevent timeouts
        max_context_length = settings.max_context_length
        if len(context) > max_context_length:
            context = context[:max_context_length] + "..."
            logger.info(f"Context truncated to {max_context_length} characters")

        # Determine language instruction
        language_instruction = self._get_language_instruction(prompt, language, settings)

        # Get role-based system prompt
        role_prompt = self._get_academic_advisor_prompt(language)

        # Combine custom instructions with language instruction and role
        all_instructions = [role_prompt, language_instruction]
        if instructions:
            all_instructions.append(instructions)
        if settings.response_instructions:
            all_instructions.append(settings.response_instructions)

        combined_instructions = " ".join(all_instructions)

        # Build conversation history section if provided
        history_section = ""
        if conversation_history and len(conversation_history) > 0:
            history_lines = ["Previous conversation:"]
            for msg in conversation_history:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role_label}: {msg['content']}")
            history_section = "\n".join(history_lines) + "\n\n"

        # Determine model to use
        model = model or self.default_model

        # Ensure model is available
        if not await self.is_available():
            raise LLMNotAvailableHTTPException("Ollama service is not available")

        if not await self.ensure_model(model):
            logger.warning(f"Model {model} not available, falling back to {self.default_model}")
            model = self.default_model
            if not await self.ensure_model(model):
                raise LLMException(f"Default model {self.default_model} is not available")

        try:
            if enable_artifacts:
                # Use Instructor for structured output with artifacts
                artifact_instruction = self._get_instructor_artifact_instruction(language)

                # Create system prompt
                system_prompt = f"""{combined_instructions}

{artifact_instruction}

You MUST return your response in the following structured format:
- text: Your main explanation/answer
- artifacts: An array of artifacts (code, diagrams, tables, visualizations) if needed

If you generate artifacts, they will be displayed in a separate panel. The text field should contain your explanation."""

                # Create user prompt
                user_prompt = f"""{history_section}Context from documents: {context}

Current question: {prompt}"""

                # Get Instructor client
                client = self._get_instructor_client()

                # Generate structured response
                structured_response: StructuredLLMResponse = await client.chat.completions.create(
                    model=model,
                    temperature=0,  # Deterministic outputs for better schema adherence
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_model=StructuredLLMResponse,
                )

                # Convert Pydantic model to dict
                response_text = structured_response.text
                artifacts = [artifact.model_dump() for artifact in structured_response.artifacts]

                # Clean up text field - remove any HTML tables or artifacts that leaked into text
                # This is a safety measure in case the LLM includes artifacts in both places
                clean_text, additional_artifacts = self._extract_artifacts(response_text)

                # Merge artifacts from Instructor and extracted artifacts (avoid duplicates)
                all_artifacts = artifacts.copy()

                # Only add extracted artifacts if they're not duplicates
                for extracted in additional_artifacts:
                    # Check if this artifact is already in the Instructor artifacts
                    is_duplicate = False
                    for existing in artifacts:
                        if (existing.get('type') == extracted.get('type') and
                            existing.get('content') == extracted.get('content')):
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        all_artifacts.append(extracted)

                result = {
                    "response": clean_text,  # Use cleaned text without artifacts
                    "artifacts": all_artifacts,
                    "model_used": model
                }

                logger.info(f"Generated {len(structured_response.artifacts)} artifact(s) using Instructor, extracted {len(additional_artifacts)} additional artifact(s) from text")

            else:
                # Fallback to regular generation without artifacts
                enhanced_prompt = f"""{history_section}Context from documents: {context}

Current question: {prompt}

Instructions: {combined_instructions} Base your answer on the provided context and previous conversation.

Answer:"""

                result = await self.generate_response(enhanced_prompt, model)
                result["artifacts"] = []

            return result

        except Exception as e:
            logger.error(f"Error in generate_with_context: {str(e)}")
            # Fallback to regex-based extraction
            logger.info("Falling back to regex-based artifact extraction")
            enhanced_prompt = f"""{history_section}Context from documents: {context}

Current question: {prompt}

Instructions: {combined_instructions} Base your answer on the provided context and previous conversation.

Answer:"""

            result = await self.generate_response(enhanced_prompt, model)

            if enable_artifacts:
                response_text = result.get("response", "")
                clean_text, artifacts = self._extract_artifacts(response_text)
                result["response"] = clean_text
                result["artifacts"] = artifacts
            else:
                result["artifacts"] = []

            return result

    def _get_academic_advisor_prompt(self, language: Optional[str]) -> str:
        """Generate academic advisor system prompt based on language."""
        is_spanish = language == "spanish" or language == "auto"

        if is_spanish:
            return """Eres un asesor académico amigable y empático de la universidad. Tu objetivo principal es ayudar al estudiante a:

1. **Planificar su progreso académico**: Ayúdalo a entender qué materias ha completado, cuáles le faltan, y cómo puede organizarse para terminar su carrera.

2. **Tomar decisiones informadas**: Oriéntalo sobre qué materias tomar próximamente, cuántas puede manejar según su historial, y cómo balancear su carga académica.

3. **Guiar su carrera profesional**: Ayúdalo a identificar sus fortalezas académicas (materias con mejores notas), áreas de mejora, y cómo sus decisiones actuales impactan su futuro profesional.

4. **Motivar y apoyar**: Sé positivo, reconoce sus logros, y ofrece consejos prácticos cuando enfrente desafíos.

**Estilo de comunicación:**
- Sé amigable, natural y conversacional (como hablarías con un amigo)
- Usa un tono cálido y empático
- Personaliza tus respuestas según el contexto del estudiante
- Celebra sus éxitos y ofrece apoyo en los desafíos
- Sé específico y práctico en tus recomendaciones
- Usa visualizaciones (tablas, gráficas) cuando ayuden a clarificar información

**Ejemplos de buen tono:**
- ❌ "Según los datos, has aprobado 8 materias."
- ✅ "¡Excelente! Ya has aprobado 8 materias. Estás haciendo un buen progreso en tu carrera."

- ❌ "Tu promedio es 72%."
- ✅ "Tu promedio actual es de 72%. Hay espacio para mejorar, y puedo ayudarte a identificar estrategias para subirlo."

- ❌ "Debes tomar Cálculo 3."
- ✅ "Te recomiendo considerar Cálculo 3 para el próximo semestre, ya que completaste Cálculo 2 con un buen desempeño del 74%."

Recuerda: No eres solo una fuente de información, eres un mentor académico que genuinamente se preocupa por el éxito del estudiante."""

        else:
            return """You are a friendly and empathetic academic advisor at the university. Your main goal is to help students:

1. **Plan their academic progress**: Help them understand which courses they've completed, what's remaining, and how to organize their path to graduation.

2. **Make informed decisions**: Guide them on which courses to take next, how many they can handle based on their history, and how to balance their academic load.

3. **Navigate their professional career**: Help them identify their academic strengths (courses with best grades), areas for improvement, and how their current decisions impact their professional future.

4. **Motivate and support**: Be positive, recognize their achievements, and offer practical advice when facing challenges.

**Communication style:**
- Be friendly, natural, and conversational (like talking to a friend)
- Use a warm and empathetic tone
- Personalize your responses based on the student's context
- Celebrate their successes and offer support during challenges
- Be specific and practical in your recommendations
- Use visualizations (tables, charts) when they help clarify information

**Examples of good tone:**
- ❌ "According to the data, you have passed 8 courses."
- ✅ "Excellent! You've already passed 8 courses. You're making good progress in your degree."

- ❌ "Your average is 72%."
- ✅ "Your current average is 72%. There's room for improvement, and I can help you identify strategies to raise it."

- ❌ "You must take Calculus 3."
- ✅ "I recommend considering Calculus 3 for next semester, since you completed Calculus 2 with a solid 74% performance."

Remember: You're not just a source of information, you're an academic mentor who genuinely cares about the student's success."""

    def _get_language_instruction(self, prompt: str, language: Optional[str], settings) -> str:
        """Generate appropriate language instruction based on preferences and detection."""
        if language == "spanish":
            return "Responde en español."
        elif language == "english":
            return "Answer in English."
        elif language == "auto" or language is None:
            # Auto-detect language from the prompt
            spanish_indicators = ['qué', 'cómo', 'cuándo', 'dónde', 'por qué', 'cuál', 'dice', 'sobre',
                                'reglamento', 'estudiantil', 'es', 'son', 'tiene', 'hay', 'puede', 'debe']
            if any(indicator.lower() in prompt.lower() for indicator in spanish_indicators):
                return "Responde en español."
            else:
                return "Answer in the same language as the question."
        else:
            return f"Answer in {language}."

    def _get_artifact_instruction(self, language: Optional[str]) -> str:
        """Generate artifact generation instructions based on language (legacy, for regex fallback)."""
        is_spanish = language == "spanish"

        if is_spanish:
            return """Si necesitas mostrar código, ejemplos, tablas, o visualizaciones, puedes generar artefactos usando esta sintaxis:
<artifact type="tipo" language="lenguaje" title="título">
contenido aquí
</artifact>

Tipos soportados: code (código), html (HTML), table (tabla), json (JSON), mermaid (diagrama).
Usa 'language' solo para código (python, javascript, etc.)."""
        else:
            return """If you need to show code, examples, tables, or visualizations, you can generate artifacts using this syntax:
<artifact type="type" language="language" title="title">
content here
</artifact>

Supported types: code, html, table, json, mermaid.
Use 'language' only for code artifacts (python, javascript, etc.)."""

    def _get_instructor_artifact_instruction(self, language: Optional[str]) -> str:
        """Generate artifact instructions for Instructor-based structured output."""
        is_spanish = language == "spanish"

        if is_spanish:
            return """IMPORTANTE: Cuando el usuario pida una tabla, código, diagrama, gráfica o cualquier visualización, DEBES crear un artifact.

Reglas para artifacts:
- SIEMPRE usa artifacts para: tablas, código, diagramas, gráficas, ejemplos de código, JSON, visualizaciones
- NO incluyas tablas markdown en el campo 'text' - ponlas en artifacts
- type: "code" (código), "html" (tablas HTML), "table" (datos tabulares), "json" (JSON), "mermaid" (diagramas/gráficas)
- title: Un título descriptivo claro
- content: El contenido completo
- language: (solo para type="code") python, javascript, java, etc.

TIPOS ESPECÍFICOS:
- Tablas de datos → type="html" con <table> HTML
- Gráficas/gráficos/charts → type="mermaid" con sintaxis mermaid (xychart, pie, bar)
- Diagramas de flujo → type="mermaid" con sintaxis mermaid (flowchart, sequenceDiagram)
- Código fuente → type="code" con language especificado

SINTAXIS MERMAID IMPORTANTE:
- En flowcharts, SIEMPRE pon texto de nodos entre comillas: A["Texto aquí"]
- NUNCA uses corchetes sin comillas: A[Texto] ❌ INCORRECTO
- Usa comillas dobles escapadas para texto: A[\\"Mi texto\\"]
- Para porcentajes o símbolos especiales: A[\\"72%\\"], B[\\"Nota: 85\\"]

Ejemplo de gráfica:
{
  "text": "Aquí está la gráfica de tus notas:",
  "artifacts": [
    {
      "type": "mermaid",
      "title": "Gráfica de Notas por Semestre",
      "content": "xychart-beta\\n  title \\"Notas por Semestre\\"\\n  x-axis [S1, S2, S3]\\n  y-axis \\"Nota\\" 0 --> 100\\n  line [70, 85, 92]"
    }
  ]
}

Ejemplo de diagrama de flujo:
{
  "text": "Aquí está el diagrama:",
  "artifacts": [
    {
      "type": "mermaid",
      "title": "Diagrama de Progreso",
      "content": "flowchart TD\\n  A[\\"Inicio\\"] --> B[\\"Paso 1\\"]\\n  B --> C[\\"Fin\\"]"
    }
  ]
}

Ejemplo de tabla:
{
  "text": "Aquí está la tabla solicitada:",
  "artifacts": [
    {
      "type": "html",
      "title": "Tabla de Datos",
      "content": "<table>...</table>"
    }
  ]
}"""
        else:
            return """IMPORTANT: When the user asks for a table, code, diagram, chart, graph or any visualization, you MUST create an artifact.

Artifact rules:
- ALWAYS use artifacts for: tables, code, diagrams, charts, graphs, code examples, JSON, visualizations
- DO NOT include markdown tables in the 'text' field - put them in artifacts
- type: "code" (code), "html" (HTML tables), "table" (tabular data), "json" (JSON), "mermaid" (diagrams/charts)
- title: A clear descriptive title
- content: The complete content
- language: (only for type="code") python, javascript, java, etc.

SPECIFIC TYPES:
- Data tables → type="html" with HTML <table>
- Charts/graphs → type="mermaid" with mermaid syntax (xychart, pie, bar)
- Flow diagrams → type="mermaid" with mermaid syntax (flowchart, sequenceDiagram)
- Source code → type="code" with language specified

IMPORTANT MERMAID SYNTAX:
- In flowcharts, ALWAYS put node text in quotes: A["Text here"]
- NEVER use brackets without quotes: A[Text] ❌ WRONG
- Use escaped double quotes for text: A[\\"My text\\"]
- For percentages or special chars: A[\\"72%\\"], B[\\"Grade: 85\\"]

Example chart artifact:
{
  "text": "Here is your grade chart:",
  "artifacts": [
    {
      "type": "mermaid",
      "title": "Grades by Semester",
      "content": "xychart-beta\\n  title \\"Grades by Semester\\"\\n  x-axis [S1, S2, S3]\\n  y-axis \\"Grade\\" 0 --> 100\\n  line [70, 85, 92]"
    }
  ]
}

Example flowchart:
{
  "text": "Here is the diagram:",
  "artifacts": [
    {
      "type": "mermaid",
      "title": "Progress Diagram",
      "content": "flowchart TD\\n  A[\\"Start\\"] --> B[\\"Step 1\\"]\\n  B --> C[\\"End\\"]"
    }
  ]
}

Example table artifact:
{
  "text": "Here is the requested table:",
  "artifacts": [
    {
      "type": "html",
      "title": "Data Table",
      "content": "<table>...</table>"
    }
  ]
}"""

    def _extract_artifacts(self, response_text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract artifacts from LLM response text.

        Returns:
            Tuple of (clean_text_without_artifacts, list_of_artifacts)
        """
        artifacts = []

        # Pattern to match <artifact> tags with attributes
        # Example: <artifact type="code" language="python" title="Example">content</artifact>
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

            # Return empty string to completely remove artifact from chat text
            return ""

        # Remove artifacts from response and collect them
        clean_text = re.sub(pattern, extract_artifact, response_text, flags=re.DOTALL)

        # Fallback: detect raw HTML tables (when LLM doesn't use artifact tags)
        table_pattern = r'<table>.*?</table>'

        def extract_table(match):
            table_content = match.group(0)

            artifact = {
                "type": "html",
                "language": None,
                "title": "Table",
                "content": table_content
            }

            artifacts.append(artifact)

            # Return empty string to remove table from chat
            return ""

        # Extract raw HTML tables
        clean_text = re.sub(table_pattern, extract_table, clean_text, flags=re.DOTALL | re.IGNORECASE)

        # Fallback: detect code blocks with triple backticks
        code_pattern = r'```(\w+)?\n(.*?)```'

        def extract_code(match):
            language = match.group(1) or "text"
            code_content = match.group(2).strip()

            artifact = {
                "type": "code",
                "language": language,
                "title": f"{language.capitalize()} Code" if language else "Code",
                "content": code_content
            }

            artifacts.append(artifact)

            # Return empty string to remove code block from chat
            return ""

        # Extract code blocks
        clean_text = re.sub(code_pattern, extract_code, clean_text, flags=re.DOTALL)

        # Fallback: detect markdown tables
        # Pattern matches tables with | separators and at least a header row and separator row
        markdown_table_pattern = r'(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)'

        def extract_markdown_table(match):
            table_content = match.group(1).strip()

            # Convert markdown table to HTML for better rendering
            lines = table_content.split('\n')
            if len(lines) < 2:
                return match.group(0)  # Not a valid table

            # Extract headers
            headers = [cell.strip() for cell in lines[0].split('|')[1:-1]]

            # Skip separator line (index 1)
            # Extract rows
            rows = []
            for line in lines[2:]:
                if line.strip():
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    rows.append(cells)

            # Build HTML table
            html_table = '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
            html_table += '  <thead>\n    <tr>\n'
            for header in headers:
                html_table += f'      <th style="padding: 8px; background-color: #f2f2f2;">{header}</th>\n'
            html_table += '    </tr>\n  </thead>\n  <tbody>\n'
            for row in rows:
                html_table += '    <tr>\n'
                for cell in row:
                    html_table += f'      <td style="padding: 8px;">{cell}</td>\n'
                html_table += '    </tr>\n'
            html_table += '  </tbody>\n</table>'

            artifact = {
                "type": "html",
                "language": None,
                "title": "Table",
                "content": html_table
            }

            artifacts.append(artifact)

            # Return empty string to remove table from chat
            return ""

        # Extract markdown tables
        clean_text = re.sub(markdown_table_pattern, extract_markdown_table, clean_text, flags=re.MULTILINE)

        # Clean up excessive newlines
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()

        logger.info(f"Extracted {len(artifacts)} artifact(s) from response")

        return clean_text, artifacts

    async def get_service_info(self) -> Dict[str, Any]:
        """Get information about the LLM service."""
        try:
            is_available = await self.is_available()

            info = {
                "service": "Ollama",
                "base_url": self.base_url,
                "is_available": is_available,
                "default_model": self.default_model
            }

            if is_available:
                try:
                    models = await self.get_available_models()
                    info["available_models"] = [m.get("name", "") for m in models]
                    info["total_models"] = len(models)
                except Exception:
                    info["available_models"] = []
                    info["total_models"] = 0

            return info

        except Exception as e:
            logger.error(f"Error getting service info: {str(e)}")
            return {
                "service": "Ollama",
                "base_url": self.base_url,
                "is_available": False,
                "error": str(e)
            }


# Global LLM service instance
llm_service = LLMService()

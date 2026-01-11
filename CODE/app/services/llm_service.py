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
            from openai import AsyncOpenAI

            ollama_client = AsyncOpenAI(
                base_url=f"{self.base_url}/v1",
                api_key="ollama",
            )
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
        """Generate a response with provided context and optional conversation history."""
        from app.core.config import get_settings
        settings = get_settings()

        max_context_length = settings.max_context_length
        if len(context) > max_context_length:
            context = context[:max_context_length] + "..."
            logger.info(f"Context truncated to {max_context_length} characters")

        language_instruction = self._get_language_instruction(prompt, language, settings)
        role_prompt = self._get_academic_advisor_prompt(language)

        all_instructions = [role_prompt, language_instruction]
        if instructions:
            all_instructions.append(instructions)
        if settings.response_instructions:
            all_instructions.append(settings.response_instructions)

        combined_instructions = " ".join(all_instructions)

        history_section = ""
        if conversation_history and len(conversation_history) > 0:
            history_lines = ["Previous conversation:"]
            for msg in conversation_history:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role_label}: {msg['content']}")
            history_section = "\n".join(history_lines) + "\n\n"

        model = model or self.default_model

        if not await self.is_available():
            raise LLMNotAvailableHTTPException("Ollama service is not available")

        if not await self.ensure_model(model):
            logger.warning(f"Model {model} not available, falling back to {self.default_model}")
            model = self.default_model
            if not await self.ensure_model(model):
                raise LLMException(f"Default model {self.default_model} is not available")

        try:
            markdown_instruction = self._get_markdown_generation_instruction(language)

            factual_instruction = ""
            if not context or context.strip() in ["", "No relevant context found.", "No relevant context found"]:
                factual_instruction = "\n\n**IMPORTANT**: No document context is available. Only answer with general knowledge. If you don't know the answer, say so explicitly - DO NOT make up specific information like addresses, names, or facts."
            else:
                factual_instruction = "\n\n**IMPORTANT**: Base your answer ONLY on the provided context from documents. If the context doesn't contain the information needed to answer the question, say so clearly - DO NOT fabricate information."

            enhanced_prompt = f"""{combined_instructions}

{markdown_instruction}
{factual_instruction}

{history_section}Context from documents: {context}

Current question: {prompt}

Answer:"""

            result = await self.generate_response(enhanced_prompt, model)

            result["response"] = self._enhance_conversational_tone(
                response=result["response"],
                user_query=prompt,
                context_available=(context and context.strip() not in ["", "No relevant context found.", "No relevant context found"])
            )

            result["artifacts"] = []

            logger.info(f"Generated markdown response with conversational enhancement")

            return result

        except Exception as e:
            logger.error(f"Error in generate_with_context: {str(e)}")
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
        """Generate academic advisor system prompt."""
        return """You are a warm, empathetic academic advisor - like a career counselor who genuinely cares about students.

**YOUR PERSONALITY:**
- Friendly and conversational (like talking to a trusted friend)
- Empathetic and supportive (acknowledge feelings before problem-solving)
- Encouraging and positive (celebrate wins, offer hope during challenges)
- Patient and clear (explain complex prerequisites step-by-step)

**CONVERSATION-FIRST APPROACH:**

1. **GREETINGS & SMALL TALK - NO TOOLS NEEDED:**
   - "Hello", "Hi", "How are you", "Thank you", "Goodbye"
   - Respond warmly: "Hi! Great to see you. I'm here to help with your academic journey. What's on your mind today?"
   - Do NOT call tools for simple greetings

2. **EMOTIONAL SUPPORT - EMPATHY FIRST, THEN TOOLS:**
   - If student seems stressed/worried/overwhelmed:
     * Start: "I understand this feels overwhelming..."
     * Then: Call tools to provide practical help
   - If student is confused:
     * Start: "Let's break this down together..."
     * Then: Use tools + diagrams to clarify
   - If student is excited:
     * Start: "I love your enthusiasm!"
     * Then: Support their goals with data

3. **INFORMATION QUERIES - USE TOOLS WITH NARRATIVE:**
   - "What courses have I completed?" → Call get_completed_courses
   - BUT frame it: "Let me pull up your transcript... [tool results] → You've completed 8 courses with a 3.4 GPA - excellent work!"
   - NEVER say "Tool returned..." - integrate data naturally

4. **PLANNING QUERIES - INTERACTIVE MULTI-TURN:**
   - "Help me plan next semester"
   - Ask clarifying questions:
     * "What's your priority this semester - lighter workload or advancing quickly?"
     * "Any specific courses you're interested in?"
   - Present options, get confirmation, THEN use create_study_plan

5. **REFLECTION QUERIES - NO NEW TOOLS:**
   - "Why did you recommend this?"
   - Explain reasoning from previous tool calls
   - Show prerequisite logic, GPA considerations, etc.

**RESPONSE STRUCTURE (ALWAYS FOLLOW):**
1. ACKNOWLEDGMENT: "Great question!" / "I can help with that."
2. MAIN CONTENT: Tool results woven into natural explanation
3. CLOSING: Follow-up question OR encouragement OR next step

**CRITICAL RULES:**
- Respond in the SAME LANGUAGE as the user's question
- Use tools when needed, but prioritize conversation quality
- Never invent courses or data - only use tool results
- If you don't have data, say so clearly and offer alternatives

**Examples of structure:**
- ❌ "You have passed 8 courses."
- ✅ "Excellent! You've passed 8 courses with a 3.4 GPA - that's solid progress. Would you like help planning what's next?"

- ❌ "Your average is 72%."
- ✅ "I see your current average is 72%. There's room to grow, and I'm here to help. Which courses have you found most challenging?"

Remember: You're not just information - you're a mentor who builds relationships and supports student success."""

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

    def _get_markdown_generation_instruction(self, language: Optional[str]) -> str:
        """
        Generate markdown-first instructions for LLM.
        Client-side parsing will extract artifacts from markdown.
        """
        is_spanish = language == "spanish"

        if is_spanish:
            return """IMPORTANTE: Usa formato markdown estándar para todas las respuestas.

FORMATO PARA VISUALIZACIONES:

1. **Tablas**: Usa tablas markdown estándar con pipes (|)
   Ejemplo:
   | Columna 1 | Columna 2 | Columna 3 |
   |-----------|-----------|-----------|
   | Dato 1    | Dato 2    | Dato 3    |
   | Dato 4    | Dato 5    | Dato 6    |

2. **Código**: Usa bloques de código con triple backtick (```)
   Ejemplo:
   ```python
   def hello():
       print("Hello world")
   ```

3. **Diagramas y Gráficas**: Usa bloques de código mermaid
   Ejemplo (diagrama de flujo):
   ```mermaid
   flowchart TD
       A["Inicio"] --> B["Paso 1"]
       B --> C["Paso 2"]
       C --> D["Fin"]
   ```

   Ejemplo (gráfica):
   ```mermaid
   xychart-beta
       title "Notas por Semestre"
       x-axis [S1, S2, S3, S4]
       y-axis "Nota" 0 --> 100
       line [70, 75, 85, 92]
   ```

   Ejemplo (gráfica de barras):
   ```mermaid
   xychart-beta
       title "Comparación de Notas"
       x-axis [Mat1, Mat2, Mat3]
       y-axis "Nota" 0 --> 100
       bar [85, 90, 78]
   ```

SINTAXIS MERMAID CRÍTICA:
- SIEMPRE usa comillas para el texto de los nodos en flowcharts: A["Texto aquí"]
- NUNCA uses corchetes sin comillas: A[Texto] ❌ INCORRECTO
- Para porcentajes o símbolos: A["72%"], B["Nota: 85"]
- En xychart: NO uses "label" después de line/bar - solo datos: line [1, 2, 3]
- En xychart: NO uses comentarios (#) en las líneas de datos - son inválidos
- Títulos SIEMPRE entre comillas: title "Mi Título"
- NO uses comentarios (//) ni (#) en mermaid - son inválidos

El cliente extraerá automáticamente las tablas, código y diagramas del markdown."""

        else:
            return """IMPORTANT: Use standard markdown format for all responses.

FORMAT FOR VISUALIZATIONS:

1. **Tables**: Use standard markdown tables with pipes (|)
   Example:
   | Column 1 | Column 2 | Column 3 |
   |----------|----------|----------|
   | Data 1   | Data 2   | Data 3   |
   | Data 4   | Data 5   | Data 6   |

2. **Code**: Use code blocks with triple backticks (```)
   Example:
   ```python
   def hello():
       print("Hello world")
   ```

3. **Diagrams and Charts**: Use mermaid code blocks
   Example (flowchart):
   ```mermaid
   flowchart TD
       A["Start"] --> B["Step 1"]
       B --> C["Step 2"]
       C --> D["End"]
   ```

   Example (chart):
   ```mermaid
   xychart-beta
       title "Grades by Semester"
       x-axis [S1, S2, S3, S4]
       y-axis "Grade" 0 --> 100
       line [70, 75, 85, 92]
   ```

   Example (bar chart):
   ```mermaid
   xychart-beta
       title "Grade Comparison"
       x-axis [Math1, Math2, Math3]
       y-axis "Grade" 0 --> 100
       bar [85, 90, 78]
   ```

CRITICAL MERMAID SYNTAX:
- ALWAYS use quotes for node text in flowcharts: A["Text here"]
- NEVER use brackets without quotes: A[Text] ❌ WRONG
- For percentages or symbols: A["72%"], B["Grade: 85"]
- In xychart: NO "label" after line/bar - just data: line [1, 2, 3]
- In xychart: NO comments (#) in data lines - they are invalid
- Titles ALWAYS quoted: title "My Title"
- NO comments (//) or (#) in mermaid - they are invalid

The client will automatically extract tables, code, and diagrams from markdown."""

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

    def _enhance_conversational_tone(
        self,
        response: str,
        user_query: str,
        context_available: bool
    ) -> str:
        """Enhance response with conversational scaffolding if missing."""
        if len(response) < 100:
            return response

        acknowledgments = ['great question', 'good question', 'i can help', 'let me help',
                          'excellent', 'excelente', 'claro', 'perfecto']
        has_acknowledgment = any(ack in response.lower()[:50] for ack in acknowledgments)

        if not has_acknowledgment:
            query_lower = user_query.lower()

            if any(word in query_lower for word in ['worried', 'stressed', 'overwhelmed']):
                opening = "I understand this can feel overwhelming. "
            elif any(word in query_lower for word in ['confused', 'lost', 'don\'t understand']):
                opening = "Let's break this down together. "
            elif any(word in query_lower for word in ['excited', 'can\'t wait']):
                opening = "I love your enthusiasm! "
            else:
                opening = "Great question! "

            response = opening + response

        ending_markers = ['?', 'keep it up', 'you\'re on track', 'next step',
                         'anything else', 'help you', '¿']
        has_closing = any(marker in response.lower()[-100:] for marker in ending_markers)

        if not has_closing:
            closing = " Is there anything else you'd like to know?"
            response = response + closing

        return response

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

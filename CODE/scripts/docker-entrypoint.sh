#!/bin/bash
set -e

echo "🐳 Starting RAG-powered Study Planning API (Docker)"

# Function to check if Ollama is available
check_ollama() {
    curl -s http://ollama:11434/api/tags > /dev/null 2>&1
    return $?
}

# Wait for Ollama service to be ready
echo "⏳ Waiting for Ollama service..."
MAX_RETRIES=30
RETRY_COUNT=0

while ! check_ollama; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Ollama service not available after ${MAX_RETRIES} attempts"
        echo "⚠️  Starting API anyway, but LLM features will not work"
        break
    fi
    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES - Waiting for Ollama..."
    sleep 2
done

if check_ollama; then
    echo "✅ Ollama service is ready"

    # Check if any models are available
    MODELS=$(curl -s http://ollama:11434/api/tags 2>/dev/null | grep -o '"name"' | wc -l)

    if [ "$MODELS" -eq 0 ]; then
        echo "📥 No models found. Pulling default model: ${OLLAMA_MODEL:-llama2:latest}"
        echo "   This may take several minutes on first run..."

        # Pull the model using Ollama API
        MODEL_NAME="${OLLAMA_MODEL:-llama2:latest}"
        curl -X POST http://ollama:11434/api/pull \
             -H "Content-Type: application/json" \
             -d "{\"name\": \"$MODEL_NAME\"}" 2>/dev/null || {
            echo "⚠️  Failed to pull model automatically"
            echo "   You can pull it manually with: docker exec study-planning-ollama ollama pull $MODEL_NAME"
        }
    else
        echo "✅ Found $MODELS model(s) in Ollama"
    fi
fi

# Ensure data directories exist (should already exist from Dockerfile, but double-check)
echo "📁 Ensuring data directories exist..."
mkdir -p /app/data/uploads
mkdir -p /app/data/chroma_db

# Execute the command passed to the container
echo "🚀 Starting FastAPI application..."
exec "$@"

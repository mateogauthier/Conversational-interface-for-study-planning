#!/bin/bash

# Start the RAG-powered Study Planning API

echo "🚀 Starting RAG-powered Study Planning API..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if requirements are installed
echo "🔍 Checking dependencies..."
python -c "import fastapi, chromadb, sentence_transformers, langchain" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Some dependencies are missing. Installing..."
    pip install -r requirements.txt
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads
mkdir -p chroma_db

# Check if Ollama is running (optional)
echo "🤖 Checking Ollama connection..."
curl -s http://localhost:11434/api/tags > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama doesn't seem to be running. LLM features may not work."
    echo "   Start Ollama with: ollama serve"
fi

# Start the API server
echo "🌐 Starting FastAPI server..."
echo "   API will be available at: http://localhost:8000"
echo "   API documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

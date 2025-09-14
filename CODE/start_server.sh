#!/bin/bash

# Start the RAG-powered Study Planning API

echo "🚀 Starting RAG-powered Study Planning API..."

# Global variables
OLLAMA_STARTED_BY_SCRIPT=false
OLLAMA_PID=""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    
    if [ "$OLLAMA_STARTED_BY_SCRIPT" = true ] && [ ! -z "$OLLAMA_PID" ]; then
        echo "🔄 Stopping Ollama service that was started by this script..."
        kill $OLLAMA_PID 2>/dev/null
        echo "✅ Ollama stopped"
    fi
    
    echo "👋 Goodbye!"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

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

# Check if Ollama is running and start it if needed
echo "🤖 Checking Ollama service..."

# Function to check if Ollama is running
check_ollama() {
    curl -s http://localhost:11434/api/tags > /dev/null 2>&1
    return $?
}

# Function to start Ollama
start_ollama() {
    echo "🔄 Starting Ollama service..."
    
    # Try using our helper script first
    if [ -f "./manage_ollama.sh" ]; then
        echo "   Using manage_ollama.sh helper..."
        ./manage_ollama.sh start
        if [ $? -eq 0 ]; then
            return 0
        fi
    fi
    
    # Method 1: Try systemctl (if Ollama is installed as a system service)
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files | grep -q ollama; then
            echo "   Using systemctl to start Ollama..."
            sudo systemctl start ollama
            sleep 3
            if check_ollama; then
                echo "✅ Ollama started via systemctl"
                return 0
            fi
        fi
    fi
    
    # Method 2: Try starting Ollama directly in background
    if command -v ollama >/dev/null 2>&1; then
        echo "   Starting Ollama in background..."
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        OLLAMA_PID=$!
        OLLAMA_STARTED_BY_SCRIPT=true
        
        # Wait up to 10 seconds for Ollama to start
        for i in {1..10}; do
            sleep 1
            if check_ollama; then
                echo "✅ Ollama started successfully (PID: $OLLAMA_PID)"
                echo "   Ollama logs: /tmp/ollama.log"
                return 0
            fi
        done
        
        # If we get here, Ollama didn't start properly
        echo "❌ Failed to start Ollama"
        kill $OLLAMA_PID 2>/dev/null
        OLLAMA_STARTED_BY_SCRIPT=false
        return 1
    fi
    
    # Method 3: Docker (if Ollama is in Docker)
    if command -v docker >/dev/null 2>&1; then
        if docker ps -a | grep -q ollama; then
            echo "   Starting Ollama Docker container..."
            docker start ollama || docker run -d --name ollama -p 11434:11434 ollama/ollama
            sleep 5
            if check_ollama; then
                echo "✅ Ollama Docker container started"
                return 0
            fi
        fi
    fi
    
    return 1
}

# Check if Ollama is already running
if check_ollama; then
    echo "✅ Ollama is already running"
else
    echo "⚠️  Ollama is not running. Attempting to start..."
    
    if start_ollama; then
        echo "🎉 Ollama is now running!"
    else
        echo "❌ Failed to automatically start Ollama."
        echo "   Please start Ollama manually using one of these methods:"
        echo "   • systemctl: sudo systemctl start ollama"
        echo "   • direct: ollama serve"
        echo "   • docker: docker run -d -p 11434:11434 ollama/ollama"
        echo ""
        echo "   The API will still start, but LLM features won't work until Ollama is running."
        read -p "   Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Startup cancelled."
            exit 1
        fi
    fi
fi

# Verify Ollama connection one more time
if check_ollama; then
    echo "🔗 Ollama connection verified"
    
    # Optional: Pull a default model if none exists
    MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | wc -l)
    if [ "$MODELS" -eq 0 ]; then
        echo "📥 No models found. Pulling default model (llama2)..."
        echo "   This may take a few minutes..."
        ollama pull llama2
    fi
else
    echo "⚠️  Ollama connection failed. LLM features will not work."
fi

# Start the API server
echo "🌐 Starting FastAPI server..."
echo "   API will be available at: http://localhost:8000"
echo "   API documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

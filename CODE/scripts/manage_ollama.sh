#!/bin/bash

# Ollama Management Helper Script
# This script helps manage Ollama service for the RAG system

OLLAMA_PORT=11434
OLLAMA_HOST="localhost"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Ollama is running
check_ollama() {
    curl -s http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags > /dev/null 2>&1
    return $?
}

# Start Ollama service
start_ollama() {
    print_status "Starting Ollama service..."
    
    if check_ollama; then
        print_warning "Ollama is already running!"
        return 0
    fi
    
    # Try different methods to start Ollama
    
    # Method 1: systemctl
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files | grep -q ollama; then
            print_status "Starting Ollama via systemctl..."
            sudo systemctl start ollama
            sleep 3
            if check_ollama; then
                print_success "Ollama started via systemctl"
                return 0
            fi
        fi
    fi
    
    # Method 2: Direct command
    if command -v ollama >/dev/null 2>&1; then
        print_status "Starting Ollama directly..."
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        echo $! > /tmp/ollama.pid
        
        # Wait for startup
        for i in {1..15}; do
            sleep 1
            if check_ollama; then
                print_success "Ollama started successfully (PID: $(cat /tmp/ollama.pid))"
                print_status "Logs available at: /tmp/ollama.log"
                return 0
            fi
        done
        
        print_error "Failed to start Ollama directly"
        return 1
    fi
    
    # Method 3: Docker
    if command -v docker >/dev/null 2>&1; then
        print_status "Trying Docker..."
        docker run -d --name ollama -p ${OLLAMA_PORT}:${OLLAMA_PORT} ollama/ollama 2>/dev/null || docker start ollama
        
        sleep 5
        if check_ollama; then
            print_success "Ollama started via Docker"
            return 0
        fi
    fi
    
    print_error "Failed to start Ollama using any method"
    return 1
}

# Stop Ollama service
stop_ollama() {
    print_status "Stopping Ollama service..."
    
    # Try systemctl first
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl is-active --quiet ollama; then
            sudo systemctl stop ollama
            print_success "Ollama stopped via systemctl"
            return 0
        fi
    fi
    
    # Try PID file
    if [ -f /tmp/ollama.pid ]; then
        PID=$(cat /tmp/ollama.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            rm -f /tmp/ollama.pid
            print_success "Ollama stopped (PID: $PID)"
            return 0
        fi
    fi
    
    # Try finding process
    OLLAMA_PID=$(pgrep -f "ollama serve")
    if [ ! -z "$OLLAMA_PID" ]; then
        kill $OLLAMA_PID
        print_success "Ollama stopped (PID: $OLLAMA_PID)"
        return 0
    fi
    
    # Try Docker
    if command -v docker >/dev/null 2>&1; then
        if docker ps | grep -q ollama; then
            docker stop ollama
            print_success "Ollama Docker container stopped"
            return 0
        fi
    fi
    
    print_warning "Ollama doesn't appear to be running"
    return 0
}

# Check Ollama status
status_ollama() {
    if check_ollama; then
        print_success "Ollama is running and responding"
        
        # Get version
        VERSION=$(curl -s http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/version 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        if [ ! -z "$VERSION" ]; then
            print_status "Version: $VERSION"
        fi
        
        # List models
        print_status "Available models:"
        curl -s http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/  - /'
        
        return 0
    else
        print_error "Ollama is not running or not responding"
        return 1
    fi
}

# Install a model
install_model() {
    local model_name=$1
    if [ -z "$model_name" ]; then
        print_error "Please specify a model name"
        print_status "Popular models: llama2, codellama, mistral, llama2:7b, llama2:13b"
        return 1
    fi
    
    if ! check_ollama; then
        print_error "Ollama is not running. Please start it first."
        return 1
    fi
    
    print_status "Installing model: $model_name"
    print_status "This may take several minutes depending on model size..."
    
    ollama pull "$model_name"
    
    if [ $? -eq 0 ]; then
        print_success "Model $model_name installed successfully"
    else
        print_error "Failed to install model $model_name"
        return 1
    fi
}

# Show usage
show_usage() {
    echo "Ollama Management Helper"
    echo "Usage: $0 {start|stop|status|restart|install MODEL_NAME}"
    echo ""
    echo "Commands:"
    echo "  start    - Start Ollama service"
    echo "  stop     - Stop Ollama service"
    echo "  status   - Check Ollama status and list models"
    echo "  restart  - Restart Ollama service"
    echo "  install  - Install a specific model"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 install llama2"
    echo "  $0 install codellama:7b"
}

# Main script logic
case "$1" in
    start)
        start_ollama
        ;;
    stop)
        stop_ollama
        ;;
    status)
        status_ollama
        ;;
    restart)
        stop_ollama
        sleep 2
        start_ollama
        ;;
    install)
        install_model "$2"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

exit $?

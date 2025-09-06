# Conversational API with RAG and OLLAMA

This project is a Python API using FastAPI, capable of making LLM requests and file manipulation using Retrieval-Augmented Generation (RAG) and OLLAMA.

## Features
- FastAPI-based REST API
- LLM requests via OLLAMA
- File manipulation endpoints
- RAG workflow integration

## Setup
1. Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn requests
   # Add ollama and RAG-related packages as needed
   ```
3. Run the API:
   ```bash
   uvicorn main:app --reload
   ```

## Folder Structure
- `main.py`: FastAPI app entry point
- `rag/`: RAG logic and utilities
- `ollama_client.py`: OLLAMA integration
- `file_utils.py`: File manipulation helpers

## Notes
- Ensure OLLAMA is running and accessible.
- Replace placeholders with actual RAG and OLLAMA logic as needed.

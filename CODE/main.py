from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging

from rag.rag_engine import retrieve_augmented_answer, process_uploaded_file, get_rag_stats
from ollama_client import query_ollama
from file_utils import save_file, list_files, delete_file, get_file_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Study Planning Conversational Interface",
    description="A RAG-powered API for study planning with document upload and intelligent querying",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class LLMRequest(BaseModel):
    prompt: str
    model: Optional[str] = None

class RAGRequest(BaseModel):
    prompt: str
    n_results: Optional[int] = 5
    use_llm: Optional[bool] = True

class RAGLLMRequest(BaseModel):
    prompt: str
    n_results: Optional[int] = 5
    model: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Study Planning Conversational Interface API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload/ - Upload documents for RAG",
            "rag": "/rag/ - Query documents using RAG",
            "rag-llm": "/rag-llm/ - RAG query with LLM completion",
            "llm": "/llm-request/ - Direct LLM query",
            "files": "/files/ - List uploaded files",
            "stats": "/rag-stats/ - RAG system statistics"
        }
    }

@app.post("/llm-request/")
async def llm_request(request: LLMRequest):
    """Direct LLM query without RAG."""
    try:
        response = query_ollama(request.prompt, request.model)
        return response
    except Exception as e:
        logger.error(f"Error in LLM request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM request failed: {str(e)}")

@app.post("/rag/")
async def rag_request(request: RAGRequest):
    """Query documents using RAG (Retrieval-Augmented Generation)."""
    try:
        rag_result = retrieve_augmented_answer(request.prompt, request.n_results)
        
        if request.use_llm and rag_result.get("context"):
            # Combine RAG context with LLM response
            enhanced_prompt = f"""Based on the following context from study documents, please answer the question:

Context:
{rag_result['context']}

Question: {request.prompt}

Please provide a comprehensive answer based on the context provided above."""
            
            llm_response = query_ollama(enhanced_prompt)
            
            return {
                "query": request.prompt,
                "rag_context": rag_result['context'],
                "llm_response": llm_response.get('response', ''),
                "n_chunks_found": rag_result['n_chunks_found'],
                "relevant_chunks": rag_result.get('relevant_chunks', [])
            }
        else:
            return rag_result
            
    except Exception as e:
        logger.error(f"Error in RAG request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG request failed: {str(e)}")

@app.post("/rag-llm/")
async def rag_llm_request(request: RAGLLMRequest):
    """Query documents using RAG with LLM completion."""
    try:
        # Get RAG context
        rag_result = retrieve_augmented_answer(request.prompt, request.n_results)
        
        if not rag_result.get("context") or rag_result.get("error"):
            return {
                "query": request.prompt,
                "error": "No relevant context found or RAG error occurred",
                "rag_result": rag_result
            }
        
        # Create enhanced prompt for LLM
        enhanced_prompt = f"""You are a study assistant helping with academic questions. Based on the following context from uploaded study documents, please provide a comprehensive and helpful answer.

Context from Documents:
{rag_result['context']}

Question: {request.prompt}

Instructions:
- Use the provided context to answer the question
- If the context doesn't fully answer the question, say so
- Provide specific references to the source documents when possible
- Be clear and educational in your response"""

        # Get LLM response
        llm_response = query_ollama(enhanced_prompt, request.model)
        
        return {
            "query": request.prompt,
            "answer": llm_response.get('response', ''),
            "context_used": rag_result['context'],
            "n_chunks_found": rag_result['n_chunks_found'],
            "sources": [chunk['metadata'].get('file_name', 'Unknown') for chunk in rag_result.get('relevant_chunks', [])],
            "relevant_chunks": rag_result.get('relevant_chunks', [])
        }
        
    except Exception as e:
        logger.error(f"Error in RAG-LLM request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG-LLM request failed: {str(e)}")

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload a document and process it for RAG."""
    try:
        # Save the file
        file_path = save_file(file)
        
        # Process the file for RAG
        success = process_uploaded_file(file_path)
        
        if success:
            return {
                "message": "File uploaded and processed successfully",
                "file_path": file_path,
                "filename": file.filename,
                "processed_for_rag": True
            }
        else:
            return {
                "message": "File uploaded but processing for RAG failed",
                "file_path": file_path,
                "filename": file.filename,
                "processed_for_rag": False,
                "warning": "The file was saved but couldn't be processed for search. Check the logs for details."
            }
            
    except Exception as e:
        logger.error(f"Error in file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@app.get("/files/")
async def get_files():
    """List all uploaded files with metadata."""
    try:
        files = list_files()
        return {
            "files": files,
            "total_files": len(files)
        }
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@app.get("/files/{filename}")
async def get_file_details(filename: str):
    """Get detailed information about a specific file."""
    try:
        file_info = get_file_info(filename)
        return file_info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/files/{filename}")
async def delete_file_endpoint(filename: str):
    """Delete a specific file."""
    try:
        success = delete_file(filename)
        if success:
            return {"message": f"File '{filename}' deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag-stats/")
async def get_rag_statistics():
    """Get RAG system statistics."""
    try:
        stats = get_rag_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting RAG stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting RAG stats: {str(e)}")

@app.get("/health/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "API is running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

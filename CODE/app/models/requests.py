"""Request models for API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class LLMRequest(BaseModel):
    """Request model for direct LLM queries."""
    prompt: str = Field(..., description="The prompt/question to send to the LLM")
    model: Optional[str] = Field(None, description="Specific model to use (optional)")


class RAGRequest(BaseModel):
    """Request model for RAG queries without LLM completion."""
    prompt: str = Field(..., description="The query to search for in documents")
    n_results: Optional[int] = Field(5, description="Number of relevant chunks to retrieve", ge=1, le=20)
    use_llm: Optional[bool] = Field(True, description="Whether to use LLM for response generation")


class RAGLLMRequest(BaseModel):
    """Request model for RAG queries with LLM completion."""
    prompt: str = Field(..., description="The query to search for and answer")
    n_results: Optional[int] = Field(5, description="Number of relevant chunks to retrieve", ge=1, le=20)
    model: Optional[str] = Field(None, description="Specific LLM model to use (optional)")


class FileDeleteRequest(BaseModel):
    """Request model for file deletion."""
    filename: str = Field(..., description="Name of the file to delete")


class ModelInstallRequest(BaseModel):
    """Request model for installing LLM models."""
    model_name: str = Field(..., description="Name of the model to install")

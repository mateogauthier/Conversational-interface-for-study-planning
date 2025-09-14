"""RAG (Retrieval-Augmented Generation) service."""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader
)
from langchain.schema import Document
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.exceptions import RAGException
from app.models.responses import RelevantChunk, RAGStatsResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    """Service for RAG operations."""
    
    def __init__(self):
        self.collection_name = settings.collection_name
        self.chromadb_path = settings.chromadb_path
        self.embedding_model_name = settings.embedding_model
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=self.chromadb_path)
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Get or create collection
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize ChromaDB collection."""
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            try:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
            except Exception as e:
                logger.error(f"Failed to create collection: {e}")
                # Create a basic collection as fallback
                self.collection = self.client.create_collection(name=self.collection_name)
                logger.info(f"Created fallback collection: {self.collection_name}")
    
    def load_document(self, file_path: str) -> List[Document]:
        """Load and parse a document based on its file extension."""
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension == '.pdf':
                loader = PyPDFLoader(file_path)
            elif file_extension in ['.txt', '.md']:
                loader = TextLoader(file_path, encoding='utf-8')
            elif file_extension in ['.doc', '.docx']:
                loader = UnstructuredWordDocumentLoader(file_path)
            elif file_extension in ['.xls', '.xlsx']:
                loader = UnstructuredExcelLoader(file_path)
            else:
                # Try to load as text file
                loader = TextLoader(file_path, encoding='utf-8')
            
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} documents from {file_path}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {str(e)}")
            raise RAGException(f"Failed to load document: {str(e)}")
    
    def process_document(self, file_path: str) -> bool:
        """Process a document and add it to the vector store."""
        try:
            # Load the document
            documents = self.load_document(file_path)
            if not documents:
                return False
            
            # Split documents into chunks
            chunks = []
            for doc in documents:
                doc_chunks = self.text_splitter.split_documents([doc])
                chunks.extend(doc_chunks)
            
            if not chunks:
                logger.warning(f"No chunks created from {file_path}")
                return False
            
            # Prepare data for ChromaDB
            texts = [chunk.page_content for chunk in chunks]
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Create unique IDs
            file_name = Path(file_path).name
            ids = [f"{file_name}_{i}" for i in range(len(chunks))]
            
            # Prepare metadata
            metadatas = []
            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": file_path,
                    "file_name": file_name,
                    "chunk_index": i,
                    **chunk.metadata
                }
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(chunks)} chunks from {file_path} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise RAGException(f"Failed to process document: {str(e)}")
    
    def retrieve_relevant_chunks(self, query: str, n_results: int = 5) -> List[RelevantChunk]:
        """Retrieve relevant document chunks for a given query."""
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, settings.max_chunks_for_context),
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            relevant_chunks = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    chunk = RelevantChunk(
                        content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i],
                        distance=results['distances'][0][i]
                    )
                    relevant_chunks.append(chunk)
            
            logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks for query")
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            raise RAGException(f"Failed to retrieve relevant chunks: {str(e)}")
    
    def generate_context(self, relevant_chunks: List[RelevantChunk]) -> str:
        """Generate context string from relevant chunks."""
        if not relevant_chunks:
            return "No relevant context found."
        
        context_parts = []
        for i, chunk in enumerate(relevant_chunks, 1):
            source = chunk.metadata.get('file_name', 'Unknown')
            content = chunk.content
            context_parts.append(f"[Source {i}: {source}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def search_documents(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search for relevant content and return formatted results."""
        try:
            # Get relevant chunks
            relevant_chunks = self.retrieve_relevant_chunks(query, n_results)
            
            # Generate context
            context = self.generate_context(relevant_chunks)
            
            return {
                "query": query,
                "context": context,
                "relevant_chunks": relevant_chunks,
                "n_chunks_found": len(relevant_chunks)
            }
        except Exception as e:
            logger.error(f"Error in search_documents: {str(e)}")
            raise RAGException(f"Document search failed: {str(e)}")
    
    def get_collection_stats(self) -> RAGStatsResponse:
        """Get statistics about the current collection."""
        try:
            count = self.collection.count()
            return RAGStatsResponse(
                collection_name=self.collection_name,
                document_count=count,
                embedding_model=self.embedding_model_name,
                total_chunks=count
            )
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise RAGException(f"Failed to get collection stats: {str(e)}")
    
    def delete_document_chunks(self, file_name: str) -> bool:
        """Delete all chunks for a specific document."""
        try:
            # Query for chunks from this file
            results = self.collection.get(
                where={"file_name": file_name},
                include=["metadatas"]
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for file {file_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting chunks for {file_name}: {str(e)}")
            raise RAGException(f"Failed to delete document chunks: {str(e)}")
    
    def reset_collection(self) -> bool:
        """Reset the entire collection (delete all documents)."""
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate it
            self._initialize_collection()
            
            logger.info(f"Reset collection: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting collection: {str(e)}")
            raise RAGException(f"Failed to reset collection: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if RAG service is available."""
        try:
            # Test collection access
            self.collection.count()
            return True
        except Exception:
            return False


# Global RAG service instance
rag_service = RAGService()

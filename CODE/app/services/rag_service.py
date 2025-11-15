"""RAG (Retrieval-Augmented Generation) service."""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from functools import partial

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader
)
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.exceptions import RAGException
from app.models.responses import RelevantChunk, RAGStatsResponse
from app.db.models import UserInDB

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
    
    def process_document(
        self,
        file_path: str,
        user_id: str,
        is_public: bool,
        filename: str
    ) -> int:
        """
        Process a document and add it to the vector store with user context.

        Args:
            file_path: Path to the document file
            user_id: MongoDB user ID (owner)
            is_public: Whether file is public (admin) or private (student)
            filename: Original filename

        Returns:
            int: Number of chunks created
        """
        try:
            # Load the document
            documents = self.load_document(file_path)
            if not documents:
                return 0

            # Split documents into chunks
            chunks = []
            for doc in documents:
                doc_chunks = self.text_splitter.split_documents([doc])
                chunks.extend(doc_chunks)

            if not chunks:
                logger.warning(f"No chunks created from {file_path}")
                return 0

            # Prepare data for ChromaDB
            texts = [chunk.page_content for chunk in chunks]
            embeddings = self.embedding_model.encode(texts).tolist()

            # Create unique IDs (include user_id to avoid conflicts)
            ids = [f"{user_id}_{filename}_{i}" for i in range(len(chunks))]

            # Prepare metadata with multi-tenancy fields
            metadatas = []
            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": file_path,
                    "file_name": filename,
                    "chunk_index": i,
                    "user_id": user_id,  # NEW: Multi-tenancy
                    "is_public": is_public,  # NEW: Public/private flag
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

            logger.info(
                f"Added {len(chunks)} chunks from {filename} to vector store "
                f"(user: {user_id}, public: {is_public})"
            )
            return len(chunks)

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise RAGException(f"Failed to process document: {str(e)}")
    
    def retrieve_relevant_chunks(
        self,
        query: str,
        user: UserInDB,
        n_results: int = 5
    ) -> List[RelevantChunk]:
        """
        Retrieve relevant document chunks based on user permissions.

        Students: Search their private files + all public files
        Admins: Search only public files

        Args:
            query: Search query
            user: Current authenticated user
            n_results: Maximum number of results

        Returns:
            List of relevant chunks with metadata
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode([query]).tolist()[0]

            # Build permission filter based on role
            where_filter = self._build_permission_filter(user)

            # Search the collection with filters
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, settings.max_chunks_for_context),
                where=where_filter,
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

            logger.info(
                f"Retrieved {len(relevant_chunks)} relevant chunks for user {user.email} "
                f"(role: {user.role})"
            )
            return relevant_chunks

        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            raise RAGException(f"Failed to retrieve relevant chunks: {str(e)}")

    def _build_permission_filter(self, user: UserInDB) -> Dict[str, Any]:
        """
        Build ChromaDB where filter based on user permissions.

        Args:
            user: Current authenticated user

        Returns:
            Dict: ChromaDB where filter
        """
        if user.role == settings.student_role:
            # Students see: their private files + all public files
            return {
                "$or": [
                    {"user_id": str(user.id)},  # Their files
                    {"is_public": True}  # All public files
                ]
            }
        elif user.role == settings.admin_role:
            # Admins see: only public files
            return {"is_public": True}
        else:
            # Unknown role, no access (return impossible filter)
            return {"user_id": "none"}
    
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
    
    def search_documents(self, query: str, user: UserInDB, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for relevant content with user-based filtering.

        Args:
            query: Search query
            user: Current authenticated user
            n_results: Maximum number of results

        Returns:
            Dict with query, context, chunks, and count
        """
        try:
            # Get relevant chunks with permission filtering
            relevant_chunks = self.retrieve_relevant_chunks(query, user, n_results)

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
    
    def delete_document_chunks(self, filename: str, user_id: str) -> bool:
        """
        Delete all chunks for a specific document belonging to a user.

        Args:
            filename: Name of the file
            user_id: MongoDB user ID (owner)

        Returns:
            bool: True if chunks were deleted
        """
        try:
            # Query for chunks from this file and user
            results = self.collection.get(
                where={
                    "$and": [
                        {"file_name": filename},
                        {"user_id": user_id}
                    ]
                },
                include=["metadatas"]
            )

            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(
                    f"Deleted {len(results['ids'])} chunks for file {filename} "
                    f"(user: {user_id})"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting chunks for {filename}: {str(e)}")
            raise RAGException(f"Failed to delete document chunks: {str(e)}")
    
    def reset_public_documents(self) -> bool:
        """
        Reset only public documents (admin use).

        Returns:
            bool: True if successful
        """
        try:
            # Get all public document IDs
            results = self.collection.get(
                where={"is_public": True},
                include=["metadatas"]
            )

            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} public chunks")

            return True

        except Exception as e:
            logger.error(f"Error resetting public documents: {str(e)}")
            raise RAGException(f"Failed to reset public documents: {str(e)}")

    def get_user_stats(self, user: UserInDB) -> RAGStatsResponse:
        """
        Get statistics for a specific user based on permissions.

        Args:
            user: Current authenticated user

        Returns:
            RAGStatsResponse with user-specific stats
        """
        try:
            where_filter = self._build_permission_filter(user)

            # Get all documents matching user permissions
            results = self.collection.get(
                where=where_filter,
                include=["metadatas"]
            )

            chunk_count = len(results['ids']) if results['ids'] else 0

            # Count unique files
            unique_files = set()
            if results['metadatas']:
                for metadata in results['metadatas']:
                    unique_files.add(metadata.get('file_name', 'unknown'))

            return RAGStatsResponse(
                collection_name=self.collection_name,
                document_count=len(unique_files),
                embedding_model=self.embedding_model_name,
                total_chunks=chunk_count
            )

        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            raise RAGException(f"Failed to get user stats: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if RAG service is available."""
        try:
            # Test collection access
            self.collection.count()
            return True
        except Exception:
            return False

    # === Async Wrapper Methods ===
    # These methods offload blocking operations to thread pool for true async behavior

    async def process_document_async(
        self,
        file_path: str,
        user_id: str,
        is_public: bool,
        filename: str
    ) -> int:
        """
        Async wrapper for process_document.
        Offloads CPU/IO-intensive operations to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self.process_document, file_path, user_id, is_public, filename)
        )

    async def retrieve_relevant_chunks_async(
        self,
        query: str,
        user: UserInDB,
        n_results: int = 5
    ) -> List[RelevantChunk]:
        """
        Async wrapper for retrieve_relevant_chunks.
        Offloads embedding generation and ChromaDB query to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self.retrieve_relevant_chunks, query, user, n_results)
        )

    async def search_documents_async(
        self,
        query: str,
        user: UserInDB,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Async wrapper for search_documents.
        Offloads search operations to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self.search_documents, query, user, n_results)
        )

    async def delete_document_chunks_async(
        self,
        filename: str,
        user_id: str
    ) -> bool:
        """
        Async wrapper for delete_document_chunks.
        Offloads ChromaDB operations to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self.delete_document_chunks, filename, user_id)
        )

    async def get_collection_stats_async(self) -> RAGStatsResponse:
        """
        Async wrapper for get_collection_stats.
        Offloads ChromaDB operations to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.get_collection_stats
        )

    async def get_user_stats_async(self, user: UserInDB) -> RAGStatsResponse:
        """
        Async wrapper for get_user_stats.
        Offloads ChromaDB operations to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self.get_user_stats, user)
        )

    async def reset_public_documents_async(self) -> bool:
        """
        Async wrapper for reset_public_documents.
        Offloads ChromaDB operations to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.reset_public_documents
        )


# Global RAG service instance
rag_service = RAGService()

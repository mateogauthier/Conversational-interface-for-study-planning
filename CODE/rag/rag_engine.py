# rag_engine.py
# RAG (Retrieval-Augmented Generation) Engine

import os
import logging
from typing import List, Dict, Any
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, collection_name: str = "study_documents"):
        self.collection_name = collection_name
        self.upload_dir = "uploads"
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            try:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {collection_name}")
            except Exception as e:
                logger.error(f"Failed to create collection: {e}")
                # Create a basic collection as fallback
                self.collection = self.client.create_collection(name=collection_name)
                logger.info(f"Created fallback collection: {collection_name}")
    
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
            return []
    
    def process_documents(self, file_path: str) -> bool:
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
            return False
    
    def retrieve_relevant_chunks(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks for a given query."""
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            relevant_chunks = []
            for i in range(len(results['documents'][0])):
                chunk = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                }
                relevant_chunks.append(chunk)
            
            logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks for query")
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []
    
    def generate_context(self, relevant_chunks: List[Dict[str, Any]]) -> str:
        """Generate context string from relevant chunks."""
        if not relevant_chunks:
            return "No relevant context found."
        
        context_parts = []
        for i, chunk in enumerate(relevant_chunks, 1):
            source = chunk['metadata'].get('file_name', 'Unknown')
            content = chunk['content']
            context_parts.append(f"[Source {i}: {source}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the current collection."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_model": "all-MiniLM-L6-v2"
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {"error": str(e)}

# Global RAG engine instance
rag_engine = RAGEngine()

def process_uploaded_file(file_path: str) -> bool:
    """Process an uploaded file and add it to the RAG system."""
    return rag_engine.process_documents(file_path)

def retrieve_augmented_answer(prompt: str, n_results: int = 5) -> Dict[str, Any]:
    """Retrieve relevant context for a given prompt."""
    try:
        # Get relevant chunks
        relevant_chunks = rag_engine.retrieve_relevant_chunks(prompt, n_results)
        
        # Generate context
        context = rag_engine.generate_context(relevant_chunks)
        
        return {
            "query": prompt,
            "context": context,
            "relevant_chunks": relevant_chunks,
            "n_chunks_found": len(relevant_chunks)
        }
    except Exception as e:
        logger.error(f"Error in retrieve_augmented_answer: {str(e)}")
        return {
            "query": prompt,
            "context": "Error retrieving context",
            "error": str(e),
            "n_chunks_found": 0
        }

def get_rag_stats() -> Dict[str, Any]:
    """Get RAG system statistics."""
    return rag_engine.get_collection_stats()

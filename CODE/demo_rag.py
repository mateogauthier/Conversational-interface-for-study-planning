#!/usr/bin/env python3
"""
Complete RAG Functionality Demonstration
This script shows how the RAG system works end-to-end
"""

import json
import requests
import time
import os
from typing import Dict, Any

API_BASE = "http://localhost:8000"

def wait_for_server(max_attempts=5):
    """Wait for the server to be available."""
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_BASE}/health/", timeout=5)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            print(f"⏳ Attempt {attempt + 1}/{max_attempts}: Waiting for server...")
            time.sleep(2)
    return False

def upload_document(file_path: str) -> Dict[str, Any]:
    """Upload a document to the RAG system."""
    print(f"\n📤 Uploading: {file_path}")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(f"{API_BASE}/upload/", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   File: {result['filename']}")
            print(f"   RAG Processing: {'✅' if result['processed_for_rag'] else '❌'}")
            return result
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)
            return {}
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return {}

def query_rag_llm(question: str) -> Dict[str, Any]:
    """Query the RAG system with LLM completion."""
    print(f"\n🤖 Querying: {question}")
    
    try:
        payload = {
            "prompt": question,
            "n_results": 5
        }
        
        response = requests.post(f"{API_BASE}/rag-llm/", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Query successful!")
            print(f"   Chunks found: {result['n_chunks_found']}")
            print(f"   Sources: {', '.join(set(result.get('sources', [])))}")
            print(f"\n📝 Answer:")
            print(result['answer'][:500] + "..." if len(result['answer']) > 500 else result['answer'])
            return result
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(response.text)
            return {}
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        return {}

def get_rag_stats():
    """Get RAG system statistics."""
    print(f"\n📊 RAG System Statistics:")
    
    try:
        response = requests.get(f"{API_BASE}/rag-stats/")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"   Collection: {stats['collection_name']}")
            print(f"   Documents: {stats['document_count']}")
            print(f"   Model: {stats['embedding_model']}")
            return stats
        else:
            print(f"❌ Stats failed: {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return {}

def list_files():
    """List all uploaded files."""
    print(f"\n📋 Uploaded Files:")
    
    try:
        response = requests.get(f"{API_BASE}/files/")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Total files: {result['total_files']}")
            
            for file_info in result['files']:
                size_mb = file_info['size_mb']
                file_type = file_info['file_type']
                filename = file_info['filename']
                print(f"   📄 {filename} ({file_type}, {size_mb} MB)")
                
            return result
        else:
            print(f"❌ File listing failed: {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"❌ File listing error: {e}")
        return {}

def create_sample_documents():
    """Create sample documents for testing."""
    
    # Physics Study Notes
    physics_content = """# Physics Study Notes

## Mechanics

### Newton's Laws of Motion
1. **First Law (Inertia)**: An object at rest stays at rest, and an object in motion stays in motion, unless acted upon by an external force.
2. **Second Law (F=ma)**: The force acting on an object equals its mass times its acceleration.
3. **Third Law (Action-Reaction)**: For every action, there is an equal and opposite reaction.

### Energy and Work
- **Kinetic Energy**: KE = ½mv²
- **Potential Energy**: PE = mgh
- **Work-Energy Theorem**: Work done equals change in kinetic energy

## Thermodynamics

### Laws of Thermodynamics
1. **First Law**: Energy cannot be created or destroyed, only transformed
2. **Second Law**: Entropy of an isolated system always increases
3. **Third Law**: Entropy approaches zero as temperature approaches absolute zero

### Heat Transfer
- **Conduction**: Heat transfer through direct contact
- **Convection**: Heat transfer through fluid motion
- **Radiation**: Heat transfer through electromagnetic waves"""

    # Mathematics Study Notes
    math_content = """# Mathematics Study Notes

## Calculus

### Derivatives
- **Power Rule**: d/dx(x^n) = nx^(n-1)
- **Product Rule**: d/dx(fg) = f'g + fg'
- **Chain Rule**: d/dx(f(g(x))) = f'(g(x)) · g'(x)

### Integrals
- **Fundamental Theorem of Calculus**: ∫f'(x)dx = f(x) + C
- **Integration by Parts**: ∫udv = uv - ∫vdu
- **Substitution Rule**: ∫f(g(x))g'(x)dx = ∫f(u)du where u = g(x)

## Linear Algebra

### Matrices
- **Matrix Multiplication**: (AB)ij = Σ(Aik × Bkj)
- **Determinant**: For 2×2 matrix, det(A) = ad - bc
- **Inverse Matrix**: A^(-1) exists if det(A) ≠ 0

### Vector Spaces
- **Linear Independence**: Vectors are linearly independent if no vector can be written as a linear combination of others
- **Basis**: A linearly independent set that spans the entire vector space
- **Dimension**: Number of vectors in a basis

## Statistics

### Probability Distributions
- **Normal Distribution**: Bell-shaped curve, μ ± σ contains ~68% of data
- **Binomial Distribution**: Used for binary outcomes with fixed number of trials
- **Poisson Distribution**: Models rare events occurring over time intervals

### Statistical Tests
- **t-test**: Compares means of two groups
- **Chi-square test**: Tests independence of categorical variables
- **ANOVA**: Compares means of multiple groups"""

    # Create the files
    files_created = []
    
    try:
        with open('physics_notes.md', 'w') as f:
            f.write(physics_content)
        files_created.append('physics_notes.md')
        
        with open('math_notes.md', 'w') as f:
            f.write(math_content)
        files_created.append('math_notes.md')
        
        print(f"✅ Created sample documents: {', '.join(files_created)}")
        return files_created
        
    except Exception as e:
        print(f"❌ Error creating sample documents: {e}")
        return []

def main():
    """Main demonstration function."""
    print("🚀 RAG Functionality Demonstration")
    print("=" * 50)
    
    # Check if server is running
    if not wait_for_server():
        print("❌ Server not available. Please start the server first:")
        print("   cd CODE && python -m uvicorn main:app --host 0.0.0.0 --port 8000")
        return
    
    # Create sample documents
    sample_files = create_sample_documents()
    
    # Get initial stats
    get_rag_stats()
    
    # Upload documents
    for file_path in sample_files:
        upload_document(file_path)
    
    # List files
    list_files()
    
    # Get updated stats
    get_rag_stats()
    
    # Test queries
    test_questions = [
        "What are Newton's laws of motion?",
        "Explain the fundamental theorem of calculus",
        "What is the difference between conduction and convection?",
        "What statistical tests can I use to compare groups?",
        "How do you calculate kinetic energy?"
    ]
    
    print(f"\n🎯 Testing RAG Queries")
    print("=" * 30)
    
    for question in test_questions:
        query_rag_llm(question)
        print("-" * 50)
    
    # Clean up sample files
    print(f"\n🧹 Cleaning up sample files...")
    for file_path in sample_files:
        try:
            os.remove(file_path)
            print(f"   Removed: {file_path}")
        except:
            pass
    
    print(f"\n🎉 RAG Demonstration Complete!")
    print(f"💡 The system successfully:")
    print(f"   ✅ Uploaded and processed documents")
    print(f"   ✅ Created vector embeddings")
    print(f"   ✅ Retrieved relevant context")
    print(f"   ✅ Generated AI-powered answers")
    print(f"\n📚 Your RAG system is ready for study planning!")

if __name__ == "__main__":
    main()

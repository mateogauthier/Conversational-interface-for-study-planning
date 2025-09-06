#!/usr/bin/env python3
"""
Test script for the RAG functionality
"""

import requests
import json
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"

def test_api_health():
    """Test if the API is running."""
    try:
        response = requests.get(f"{BASE_URL}/health/")
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print("❌ API health check failed")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running.")
        return False

def test_upload_sample_file():
    """Upload a sample text file for testing."""
    # Create a sample study document
    sample_content = """
    # Introduction to Machine Learning

    Machine Learning (ML) is a subset of artificial intelligence (AI) that provides systems the ability to automatically learn and improve from experience without being explicitly programmed. ML focuses on the development of computer programs that can access data and use it to learn for themselves.

    ## Types of Machine Learning

    ### 1. Supervised Learning
    Supervised learning is where you have input variables (X) and an output variable (Y) and you use an algorithm to learn the mapping function from the input to the output.

    ### 2. Unsupervised Learning
    Unsupervised learning is where you only have input data (X) and no corresponding output variables. The goal is to model the underlying structure or distribution in the data.

    ### 3. Reinforcement Learning
    Reinforcement learning is an area of machine learning concerned with how agents ought to take actions in an environment to maximize cumulative reward.

    ## Key Concepts

    - **Algorithm**: A set of rules or instructions given to an AI, neural network, or other machine to help it learn on its own.
    - **Training Data**: The dataset used to teach a machine learning algorithm.
    - **Feature**: An individual measurable property or characteristic of a phenomenon being observed.
    - **Model**: The output of an algorithm after training on a dataset.
    """
    
    # Save sample file
    sample_file_path = "sample_ml_notes.txt"
    with open(sample_file_path, "w") as f:
        f.write(sample_content)
    
    try:
        # Upload the file
        with open(sample_file_path, "rb") as f:
            files = {"file": (sample_file_path, f, "text/plain")}
            response = requests.post(f"{BASE_URL}/upload/", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ File uploaded successfully: {result['filename']}")
            print(f"   Processed for RAG: {result['processed_for_rag']}")
            return True
        else:
            print(f"❌ File upload failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error uploading file: {str(e)}")
        return False
    finally:
        # Clean up sample file
        if os.path.exists(sample_file_path):
            os.remove(sample_file_path)

def test_rag_query():
    """Test RAG query functionality."""
    query = "What are the different types of machine learning?"
    
    try:
        response = requests.post(
            f"{BASE_URL}/rag-llm/",
            json={"prompt": query, "n_results": 3}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ RAG query successful")
            print(f"   Query: {result['query']}")
            print(f"   Chunks found: {result['n_chunks_found']}")
            print(f"   Answer: {result['answer'][:200]}...")
            return True
        else:
            print(f"❌ RAG query failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error in RAG query: {str(e)}")
        return False

def test_list_files():
    """Test file listing functionality."""
    try:
        response = requests.get(f"{BASE_URL}/files/")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ File listing successful")
            print(f"   Total files: {result['total_files']}")
            for file_info in result['files'][:3]:  # Show first 3 files
                print(f"   - {file_info['filename']} ({file_info['file_type']})")
            return True
        else:
            print(f"❌ File listing failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error listing files: {str(e)}")
        return False

def test_rag_stats():
    """Test RAG statistics."""
    try:
        response = requests.get(f"{BASE_URL}/rag-stats/")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ RAG stats retrieved")
            print(f"   Collection: {result['collection_name']}")
            print(f"   Document count: {result['document_count']}")
            print(f"   Embedding model: {result['embedding_model']}")
            return True
        else:
            print(f"❌ RAG stats failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting RAG stats: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing RAG Functionality")
    print("=" * 40)
    
    tests = [
        ("API Health Check", test_api_health),
        ("Upload Sample File", test_upload_sample_file),
        ("RAG Query Test", test_rag_query),
        ("List Files", test_list_files),
        ("RAG Statistics", test_rag_stats),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
        
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! RAG system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()

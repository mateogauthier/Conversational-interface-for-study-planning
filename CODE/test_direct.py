#!/usr/bin/env python3
"""
Simple test of RAG functionality directly
"""

import sys
import os
sys.path.append('.')

def test_rag_engine_directly():
    """Test RAG engine functionality directly without API."""
    print("🧪 Testing RAG Engine Directly")
    print("=" * 40)
    
    try:
        from rag.rag_engine import rag_engine
        
        # Test 1: Check collection stats
        print("\n📊 Collection Stats:")
        stats = rag_engine.get_collection_stats()
        print(f"   Collection: {stats['collection_name']}")
        print(f"   Documents: {stats['document_count']}")
        print(f"   Embedding Model: {stats['embedding_model']}")
        
        # Test 2: Process a test document
        print("\n📄 Processing Test Document:")
        test_file = "test_document.md"
        if os.path.exists(test_file):
            success = rag_engine.process_documents(test_file)
            if success:
                print(f"   ✅ Successfully processed {test_file}")
                
                # Check stats again
                stats = rag_engine.get_collection_stats()
                print(f"   📊 Updated document count: {stats['document_count']}")
            else:
                print(f"   ❌ Failed to process {test_file}")
        else:
            print(f"   ❌ Test file {test_file} not found")
        
        # Test 3: Query the documents
        print("\n🔍 Testing Query:")
        query = "What are the types of machine learning?"
        result = rag_engine.retrieve_relevant_chunks(query, n_results=3)
        
        if result:
            print(f"   ✅ Found {len(result)} relevant chunks")
            for i, chunk in enumerate(result[:2], 1):
                print(f"   Chunk {i}: {chunk['content'][:100]}...")
                print(f"   Distance: {chunk['distance']:.4f}")
        else:
            print("   ❌ No relevant chunks found")
            
        # Test 4: Generate context
        print("\n📝 Testing Context Generation:")
        context = rag_engine.generate_context(result)
        print(f"   Context length: {len(context)} characters")
        if context:
            print(f"   ✅ Context generated successfully")
            print(f"   Preview: {context[:200]}...")
        else:
            print("   ❌ No context generated")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing RAG engine: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_file_utils():
    """Test file utilities."""
    print("\n🗂️  Testing File Utils")
    print("=" * 40)
    
    try:
        from file_utils import is_supported_file, get_file_type
        
        # Test supported file types
        test_files = ["doc.pdf", "notes.txt", "data.xlsx", "readme.md", "script.py"]
        for filename in test_files:
            supported = is_supported_file(filename)
            file_type = get_file_type(filename)
            status = "✅" if supported else "❌"
            print(f"   {status} {filename} -> {file_type}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing file utils: {str(e)}")
        return False

def main():
    """Run direct tests."""
    print("🚀 Direct RAG Testing (No Server Required)")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_file_utils():
        tests_passed += 1
        
    if test_rag_engine_directly():
        tests_passed += 1
    
    print(f"\n🎯 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All direct tests passed!")
        print("\n💡 To test the API endpoints:")
        print("   1. Start server: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
        print("   2. Test API: python test_rag.py")
        print("   3. View docs: http://localhost:8000/docs")
    else:
        print("⚠️  Some tests failed.")

if __name__ == "__main__":
    main()

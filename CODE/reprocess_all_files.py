#!/usr/bin/env python3
"""Script to reprocess all files from GridFS into ChromaDB."""

import asyncio
import os
import tempfile
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from bson import ObjectId
from app.services.rag_service import rag_service

async def reprocess_all_files():
    """Reprocess all files from GridFS into ChromaDB."""
    # Connect to MongoDB
    client = AsyncIOMotorClient('mongodb://admin:password@mongodb:27017/?authSource=admin')
    db = client['study_planning']

    # Initialize GridFS
    fs = AsyncIOMotorGridFSBucket(db)

    # Get all file metadata
    files = await db.file_metadata.find({}).to_list(length=1000)

    print(f"Found {len(files)} files to reprocess from GridFS")

    processed = 0
    failed = 0

    for file_doc in files:
        filename = file_doc['filename']
        user_id = file_doc.get('user_id')
        is_public = file_doc.get('is_public', False)
        file_id = file_doc.get('gridfs_file_id')  # GridFS file ID

        print(f"\nProcessing: {filename}")
        print(f"  User: {user_id}")
        print(f"  Public: {is_public}")
        print(f"  GridFS ID: {file_id}")

        if not file_id:
            print(f"  ❌ No gridfs_file_id found")
            failed += 1
            continue

        try:
            # Ensure file_id is ObjectId
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)

            # Create temporary file to download from GridFS
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
                temp_path = tmp_file.name

                # Download file from GridFS
                grid_out = await fs.open_download_stream(file_id)
                content = await grid_out.read()
                tmp_file.write(content)
                tmp_file.flush()

            print(f"  Downloaded to: {temp_path}")

            # Process document into ChromaDB
            chunk_count = rag_service.process_document(
                file_path=temp_path,
                user_id=user_id,
                is_public=is_public,
                filename=filename
            )

            # Update chunk count in MongoDB
            await db.file_metadata.update_one(
                {'_id': file_doc['_id']},
                {'$set': {'chunk_count': chunk_count}}
            )

            print(f"  ✅ Successfully processed {chunk_count} chunks")
            processed += 1

            # Clean up temporary file
            os.unlink(temp_path)

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1

            # Try to clean up temp file if it exists
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass

    print(f"\n{'='*60}")
    print(f"Reprocessing complete!")
    print(f"  Processed: {processed}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(files)}")
    print(f"{'='*60}")

    # Verify ChromaDB count
    if processed > 0:
        try:
            import chromadb
            from chromadb.config import Settings
            chroma_client = chromadb.HttpClient(
                host='chromadb-server',
                port=8000,
                settings=Settings(anonymized_telemetry=False)
            )
            collection = chroma_client.get_collection('study_documents')
            total_chunks = collection.count()
            print(f"\nTotal chunks in ChromaDB: {total_chunks}")
        except Exception as e:
            print(f"\nCould not verify ChromaDB count: {e}")

    client.close()

if __name__ == "__main__":
    asyncio.run(reprocess_all_files())

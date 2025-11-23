"""
Migration script to move existing files from local filesystem to GridFS.

This script:
1. Reads all files from data/uploads/ directory
2. Uploads them to GridFS
3. Updates file_metadata collection with gridfs_file_id
4. Optionally deletes local files after successful migration

Usage:
    python scripts/migrate_files_to_gridfs.py [--delete-local]
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from bson import ObjectId
from app.core.config import get_settings

settings = get_settings()


async def migrate_files_to_gridfs(delete_local: bool = False):
    """
    Migrate files from local filesystem to GridFS.

    Args:
        delete_local: If True, delete local files after successful migration
    """
    print("=" * 60)
    print("File Migration Script: Filesystem → GridFS")
    print("=" * 60)

    # Connect to MongoDB
    print(f"\n📡 Connecting to MongoDB: {settings.mongo_uri}")
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_database_name]
    fs_bucket = AsyncIOMotorGridFSBucket(db)
    files_collection = db["file_metadata"]

    try:
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return

    # Get upload directory
    upload_dir = Path(settings.upload_dir)

    if not upload_dir.exists():
        print(f"\n⚠️  Upload directory not found: {upload_dir}")
        print("   No files to migrate.")
        return

    # Get all files in upload directory
    files_to_migrate = []
    for file_path in upload_dir.rglob("*"):
        if file_path.is_file():
            files_to_migrate.append(file_path)

    if not files_to_migrate:
        print(f"\n⚠️  No files found in {upload_dir}")
        return

    print(f"\n📂 Found {len(files_to_migrate)} files to migrate")
    print("-" * 60)

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in files_to_migrate:
        filename = file_path.name
        print(f"\n📄 Processing: {filename}")

        try:
            # Check if file metadata exists in MongoDB
            file_metadata = await files_collection.find_one({"filename": filename})

            if not file_metadata:
                print(f"   ⚠️  No metadata found in MongoDB - skipping")
                skipped_count += 1
                continue

            # Check if already migrated
            if file_metadata.get("gridfs_file_id"):
                print(f"   ✓ Already migrated (GridFS ID: {file_metadata['gridfs_file_id']})")
                skipped_count += 1
                continue

            # Read file content
            with open(file_path, "rb") as f:
                content = f.read()

            file_size = len(content)
            print(f"   📊 Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

            # Upload to GridFS
            gridfs_file_id = await fs_bucket.upload_from_stream(
                filename,
                content,
                metadata={
                    "user_id": file_metadata.get("user_id"),
                    "auth0_id": file_metadata.get("auth0_id"),
                    "is_public": file_metadata.get("is_public", False),
                    "file_type": file_metadata.get("file_type", ""),
                    "uploaded_at": file_metadata.get("uploaded_at", datetime.utcnow()),
                    "migrated_at": datetime.utcnow()
                }
            )

            print(f"   ☁️  Uploaded to GridFS: {gridfs_file_id}")

            # Update file metadata with GridFS ID
            await files_collection.update_one(
                {"_id": file_metadata["_id"]},
                {
                    "$set": {
                        "gridfs_file_id": str(gridfs_file_id),
                        "migrated_at": datetime.utcnow()
                    }
                }
            )

            print(f"   ✅ Updated metadata with GridFS ID")

            # Delete local file if requested
            if delete_local:
                file_path.unlink()
                print(f"   🗑️  Deleted local file")

            migrated_count += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            error_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"✅ Migrated: {migrated_count}")
    print(f"⏭️  Skipped: {skipped_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total: {len(files_to_migrate)}")

    if delete_local and migrated_count > 0:
        print(f"\n🗑️  {migrated_count} local files deleted")

    # Close connection
    client.close()
    print("\n✅ Migration complete!")


async def verify_migration():
    """Verify that all files in metadata have GridFS IDs."""
    print("\n" + "=" * 60)
    print("Verifying Migration")
    print("=" * 60)

    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_database_name]
    files_collection = db["file_metadata"]

    try:
        # Count total files
        total_count = await files_collection.count_documents({})

        # Count files with GridFS ID
        migrated_count = await files_collection.count_documents(
            {"gridfs_file_id": {"$exists": True, "$ne": None}}
        )

        # Count files without GridFS ID
        not_migrated_count = await files_collection.count_documents(
            {"$or": [
                {"gridfs_file_id": {"$exists": False}},
                {"gridfs_file_id": None}
            ]}
        )

        print(f"\n📊 Total files in metadata: {total_count}")
        print(f"✅ Migrated to GridFS: {migrated_count}")
        print(f"⚠️  Not migrated: {not_migrated_count}")

        if not_migrated_count > 0:
            print("\n⚠️  Files without GridFS ID:")
            cursor = files_collection.find(
                {"$or": [
                    {"gridfs_file_id": {"$exists": False}},
                    {"gridfs_file_id": None}
                ]},
                {"filename": 1, "user_id": 1}
            )
            async for doc in cursor:
                print(f"   - {doc['filename']} (user: {doc.get('user_id', 'unknown')})")

        print("\n✅ Verification complete!")

    finally:
        client.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate files from local filesystem to GridFS"
    )
    parser.add_argument(
        "--delete-local",
        action="store_true",
        help="Delete local files after successful migration"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify migration status without migrating"
    )

    args = parser.parse_args()

    if args.verify:
        await verify_migration()
    else:
        if args.delete_local:
            print("\n⚠️  WARNING: Local files will be deleted after migration!")
            response = input("Continue? (yes/no): ")
            if response.lower() != "yes":
                print("Migration cancelled.")
                return

        await migrate_files_to_gridfs(delete_local=args.delete_local)
        await verify_migration()


if __name__ == "__main__":
    asyncio.run(main())

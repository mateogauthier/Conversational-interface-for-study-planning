# Auth0 + RBAC Implementation Status

## Overview

This document tracks the implementation progress of Auth0 authentication with role-based access control (RBAC) for the Study Planning API.

**Implementation Date**: January 2025
**Status**: 🟡 **IN PROGRESS** (Core infrastructure complete, routes need updating)

---

## ✅ Completed Components

### Phase 1: Foundation & Infrastructure

- [x] **Dependencies added** ([requirements.txt](CODE/requirements.txt))
  - motor (async MongoDB)
  - pymongo
  - python-jose (JWT)
  - python-auth0
  - passlib

- [x] **Database Layer** ([app/db/](CODE/app/db/))
  - `database.py` - MongoDB connection with Motor
  - `models.py` - Pydantic models (UserInDB, FileMetadataInDB)
  - `collections.py` - Collection name constants

- [x] **Configuration** ([app/core/config.py](CODE/app/core/config.py))
  - Auth0 settings (domain, audience, algorithms)
  - MongoDB connection string
  - Role definitions (admin, student)
  - Updated CORS to restrict origins

- [x] **Security Utilities** ([app/core/security.py](CODE/app/core/security.py))
  - JWT verification with Auth0 JWKS
  - Token decoding and validation
  - Role extraction from JWT claims
  - JWKS caching for performance

- [x] **Exception Handling** ([app/core/exceptions.py](CODE/app/core/exceptions.py))
  - `AuthenticationException`
  - `AuthorizationException`
  - `TokenExpiredException`
  - `UserNotFoundException`
  - HTTP exceptions (401, 403)

### Phase 2: Services

- [x] **Auth Service** ([app/services/auth_service.py](CODE/app/services/auth_service.py))
  - Token authentication
  - User creation/sync from Auth0
  - Role checking

- [x] **User Service** ([app/services/user_service.py](CODE/app/services/user_service.py))
  - User CRUD operations
  - Statistics tracking (uploads, queries, storage)
  - System-wide statistics (admin)

- [x] **File Service Updates** ([app/services/file_service.py](CODE/app/services/file_service.py))
  - Multi-tenant file storage
  - MongoDB metadata tracking
  - Permission-based file listing
  - Permission-based file deletion
  - File ownership checking

### Phase 3: API Dependencies

- [x] **Authentication Dependencies** ([app/api/dependencies.py](CODE/app/api/dependencies.py))
  - `get_current_user()` - JWT validation
  - `get_current_admin()` - Admin-only dependency
  - `get_current_student()` - Student-only dependency
  - Service factory functions

### Phase 4: User Models

- [x] **User API Models** ([app/models/user.py](CODE/app/models/user.py))
  - `UserResponse` - User profile
  - `UserStatisticsResponse` - Usage statistics
  - `UserProfileUpdate` - Profile updates
  - `UserListResponse` - User listing
  - `FileOwnershipInfo` - File metadata

### Phase 5: Documentation

- [x] **Environment Template** ([CODE/.env.example](CODE/.env.example))
  - Auth0 configuration
  - MongoDB configuration
  - All required environment variables

- [x] **Auth0 Setup Guide** ([AUTH_SETUP.md](AUTH_SETUP.md))
  - Step-by-step Auth0 configuration
  - Role setup instructions
  - JWT token configuration
  - Troubleshooting guide

---

## 🟡 In Progress / Pending Components

### RAG Service Updates

**File**: [app/services/rag_service.py](CODE/app/services/rag_service.py)

**Required Changes**:
1. Add `user_id` and `is_public` to ChromaDB metadata when processing documents
2. Update `retrieve_relevant_chunks()` to filter by user permissions:
   - Students: `{"$or": [{"is_public": True}, {"user_id": user_id}]}`
   - Admins: `{"is_public": True}`
3. Update `generate_context()` to respect filtered results
4. Add method to delete documents by user/public status

**Example**:
```python
# In process_document()
metadata={
    "source": source_file,
    "chunk_index": i,
    "user_id": user_id,  # NEW
    "is_public": is_public,  # NEW
    "filename": filename  # NEW
}

# In retrieve_relevant_chunks()
if user.role == "student":
    where_filter = {
        "$or": [
            {"is_public": True},
            {"user_id": str(user.id)}
        ]
    }
elif user.role == "admin":
    where_filter = {"is_public": True}
```

---

### Route Updates

#### Files Routes ([app/api/routes/files.py](CODE/app/api/routes/files.py))

**Required Changes**:
1. Add `current_user: UserInDB = Depends(get_current_user)` to all endpoints
2. Update `upload_file()`:
   - Determine `is_public` based on user role
   - Pass user and is_public to `file_service.save_file()`
   - Call `rag_service.process_document()` with metadata
   - Update user statistics
3. Update `list_files()`:
   - Pass user to `file_service.list_files(user)`
   - Return FileMetadataInDB list
4. Update `delete_file()`:
   - Pass user to `file_service.delete_file(filename, user)`
   - Update user statistics
   - Delete from RAG collection

**Status**: ⏳ Not started

---

#### RAG Routes ([app/api/routes/rag.py](CODE/app/api/routes/rag.py))

**Required Changes**:
1. Add `current_user: UserInDB = Depends(get_current_user)` to all endpoints
2. Update `search()`:
   - Pass user to `rag_service.retrieve_relevant_chunks()` for filtering
3. Update `query()`:
   - Pass user for filtered search
   - Increment user query statistics
4. Update `reset()`:
   - Make admin-only: `admin = Depends(get_current_admin)`
   - Only reset public files
5. Update `stats()`:
   - Return user-specific or global stats based on role

**Status**: ⏳ Not started

---

#### LLM Routes ([app/api/routes/llm.py](CODE/app/api/routes/llm.py))

**Required Changes**:
1. Add `current_user: UserInDB = Depends(get_current_user)` to all endpoints
2. Update `ensure_model()`:
   - Make admin-only: `admin = Depends(get_current_admin)`

**Status**: ⏳ Not started

---

### New Routes

#### User Profile Routes ([app/api/routes/users.py](CODE/app/api/routes/users.py))

**Create New File** with endpoints:
- `GET /users/me` - Current user profile
- `GET /users/me/stats` - Personal statistics
- `PATCH /users/me` - Update profile (name, preferences)

**Status**: ⏳ Not started

---

#### Admin Routes ([app/api/routes/admin.py](CODE/app/api/routes/admin.py))

**Create New File** with endpoints:
- `GET /admin/users` - List all users
- `GET /admin/users/{user_id}` - User details
- `GET /admin/users/{user_id}/stats` - User statistics
- `GET /admin/stats` - System-wide statistics

All endpoints require: `admin = Depends(get_current_admin)`

**Status**: ⏳ Not started

---

### Main Application Updates

#### Main App ([app/main.py](CODE/app/main.py))

**Required Changes**:
1. Add database lifecycle events:
   ```python
   @app.on_event("startup")
   async def startup():
       await mongodb.connect()

   @app.on_event("shutdown")
   async def shutdown():
       await mongodb.disconnect()
   ```

2. Initialize file service with database:
   ```python
   from app.db.database import mongodb
   from app.services.file_service import get_file_service_instance

   @app.on_event("startup")
   async def init_services():
       get_file_service_instance(mongodb.get_database())
   ```

3. Register new routers:
   ```python
   from app.api.routes import users, admin
   app.include_router(users.router)
   app.include_router(admin.router)
   ```

4. Add exception handlers for auth exceptions

**Status**: ⏳ Not started

---

#### Dependencies Update ([app/api/dependencies.py](CODE/app/api/dependencies.py))

**Required Changes**:
1. Update `get_file_service()` to use new factory pattern with database

**Status**: ⏳ Not started

---

### Docker Configuration

#### Docker Compose ([docker-compose.yml](docker-compose.yml))

**Required Changes**:
1. Add MongoDB service:
   ```yaml
   mongodb:
     image: mongo:7.0
     container_name: study-planning-mongodb
     environment:
       MONGO_INITDB_ROOT_USERNAME: admin
       MONGO_INITDB_ROOT_PASSWORD: password
     volumes:
       - mongo-data:/data/db
     ports:
       - "27017:27017"  # Expose for development
   ```

2. Update fastapi-app:
   - Add `depends_on: [mongodb]`
   - Add environment variables for Auth0 and MongoDB

3. Add volume:
   ```yaml
   volumes:
     mongo-data:
   ```

**Status**: ⏳ Not started

---

#### Docker Compose Production ([docker-compose.prod.yml](docker-compose.prod.yml))

**Required Changes**:
- Same as docker-compose.yml but:
  - Don't expose MongoDB port (internal only)
  - Use production-grade MongoDB configuration
  - Add authentication and security settings

**Status**: ⏳ Not started

---

### Scripts

#### MongoDB Initialization ([scripts/init_mongodb.py](scripts/init_mongodb.py))

**Create New File** to:
1. Create MongoDB indexes:
   - `users.auth0_id` (unique)
   - `users.email` (unique)
   - `file_metadata.filename` (unique)
   - `file_metadata.user_id`
   - `file_metadata.is_public`

2. Run on startup before FastAPI launches

**Status**: ⏳ Not started

---

#### Docker Entrypoint Updates ([CODE/scripts/docker-entrypoint.sh](CODE/scripts/docker-entrypoint.sh))

**Required Changes**:
1. Add MongoDB health check:
   ```bash
   wait-for-it mongodb:27017 --timeout=60
   ```

2. Run MongoDB initialization script:
   ```bash
   python scripts/init_mongodb.py
   ```

**Status**: ⏳ Not started

---

### Documentation Updates

#### README Update ([README.md](README.md))

**Required Sections**:
1. Authentication overview
2. Auth0 setup link
3. Environment variables for Auth0
4. Role descriptions (admin vs student)
5. API authentication examples

**Status**: ⏳ Not started

---

#### CLAUDE.md Update ([CLAUDE.md](CLAUDE.md))

**Required Sections**:
1. Authentication architecture
2. MongoDB integration
3. Multi-tenancy design
4. Permission model
5. File ownership model

**Status**: ⏳ Not started

---

## 🔴 Not Started Components

### Testing

- [ ] `tests/test_auth.py` - Authentication tests
- [ ] `tests/test_user_service.py` - User service tests
- [ ] `tests/test_rbac.py` - Role-based access tests
- [ ] Update existing tests with mock authentication

---

## Implementation Priority

### High Priority (Core Functionality)

1. ✅ Complete RAG service metadata filtering
2. ✅ Update file routes with authentication
3. ✅ Update RAG routes with filtering
4. ✅ Update LLM routes with authentication
5. ✅ Add MongoDB to docker-compose
6. ✅ Update main.py with database lifecycle
7. ✅ Fix dependencies.py file service pattern

### Medium Priority (User Features)

8. ✅ Create user profile routes
9. ✅ Create admin routes
10. ✅ Update docker-entrypoint.sh
11. ✅ Create MongoDB initialization script

### Low Priority (Documentation & Testing)

12. ✅ Update README.md
13. ✅ Update CLAUDE.md
14. ✅ Create tests

---

## Quick Start for Developers

### To Continue Implementation:

1. **Next Task**: Update RAG service with metadata filtering
   - File: `app/services/rag_service.py`
   - Add user context to all methods
   - Implement permission filtering

2. **After RAG Service**: Update routes in this order:
   - Files routes (most critical)
   - RAG routes (depends on RAG service)
   - LLM routes (simplest)

3. **Then**: Docker configuration
   - Add MongoDB to docker-compose.yml
   - Test with `docker compose up`

### Testing the Implementation:

```bash
# 1. Set up Auth0 (see AUTH_SETUP.md)

# 2. Copy environment template
cp CODE/.env.example CODE/.env

# 3. Fill in Auth0 credentials in CODE/.env

# 4. Start with Docker
docker compose up

# 5. Get access token from Auth0

# 6. Test authentication
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/users/me
```

---

## Architecture Summary

### User Roles & Permissions

| Role | Upload | Own Files | Public Files | Others' Private Files |
|------|--------|-----------|--------------|---------------------|
| **Student** | Private | ✅ Full Access | ✅ Read + Query | ❌ No Access |
| **Admin** | Public | ✅ Full Access | ✅ Full Access | ❌ No Access |

### RAG Query Behavior

- **Student queries**: Search their private files + all public files
- **Admin queries**: Search only public files

### File Visibility

- **Public files**: Uploaded by admins, visible to everyone
- **Private files**: Uploaded by students, visible only to owner

---

## Notes for Future Development

### Potential Enhancements

1. **Teacher Role** (mentioned for future):
   - Subject-specific public files
   - Restricted public file management
   - Requires additional metadata field: `subject`

2. **File Sharing**:
   - Students share private files with others
   - Temporary access links

3. **File Versioning**:
   - Track file updates
   - Version history

4. **Advanced Analytics**:
   - Query performance metrics
   - Popular documents tracking
   - User engagement statistics

### Technical Debt

- File service singleton pattern needs refinement
- Consider adding Redis for session caching
- Implement rate limiting per user
- Add audit logging for admin actions

---

## Contact & Support

For questions about this implementation:
- Review [AUTH_SETUP.md](AUTH_SETUP.md) for Auth0 configuration
- Check [CODE/.env.example](CODE/.env.example) for required environment variables
- See existing services for implementation patterns

**Last Updated**: January 2025

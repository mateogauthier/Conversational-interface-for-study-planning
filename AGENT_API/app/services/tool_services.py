"""Service layer for agent tool execution.

This module connects to the main API via HTTP endpoints instead of direct imports,
making the agent-api truly independent and avoiding module namespace conflicts.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx
from duckduckgo_search import DDGS

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentToolService:
    """Service for executing agent tools via HTTP calls to main API."""

    def __init__(self):
        """Initialize tool service."""
        self.main_api_url = settings.main_api_url.rstrip("/")
        self.http_client: Optional[httpx.AsyncClient] = None
        logger.info(f"AgentToolService initialized with main API URL: {self.main_api_url}")

    async def initialize(self):
        """Initialize HTTP client."""
        try:
            self.http_client = httpx.AsyncClient(
                base_url=self.main_api_url,
                timeout=30.0,
                follow_redirects=True
            )
            logger.info("HTTP client initialized successfully")

            # Test connection to main API
            try:
                response = await self.http_client.get("/health")
                if response.status_code == 200:
                    logger.info("Successfully connected to main API")
                else:
                    logger.warning(f"Main API health check returned status {response.status_code}")
            except Exception as e:
                logger.warning(f"Could not reach main API health endpoint: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize HTTP client: {e}")
            raise

    async def shutdown(self):
        """Shutdown HTTP client."""
        try:
            if self.http_client:
                await self.http_client.aclose()
                logger.info("HTTP client closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def _create_auth_header(self, user_auth0_id: str, user_role: str) -> Dict[str, str]:
        """Create authorization header for requests to main API.

        Uses service-to-service authentication with shared secret key.

        Args:
            user_auth0_id: User's Auth0 ID
            user_role: User's role (student/admin)

        Returns:
            Dict of headers
        """
        return {
            "X-User-Auth0-ID": user_auth0_id,
            "X-User-Role": user_role,
            "X-Service-Key": settings.internal_service_key,
        }

    async def search_documents(
        self,
        query: str,
        n_results: int,
        user_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Search documents using RAG service via main API.

        Args:
            query: Search query
            n_results: Number of results to return
            user_id: User ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with search results
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            # Call main API's RAG search endpoint (no trailing slash to avoid redirect)
            headers = self._create_auth_header(user_auth0_id, user_role)
            logger.info(f"Sending headers to main API: {list(headers.keys())}")

            response = await self.http_client.post(
                "/rag/search",
                json={
                    "prompt": query,  # Main API expects 'prompt', not 'query'
                    "n_results": n_results
                },
                headers=headers
            )

            response.raise_for_status()
            data = response.json()

            # Format response to match expected structure
            chunks = []
            for chunk in data.get("relevant_chunks", [])[:n_results]:
                # DO NOT truncate chunk content - agents need full context
                chunks.append({
                    "content": chunk.get("content", ""),
                    "source": chunk.get("metadata", {}).get("file_name", "Unknown"),
                    "chunk_index": chunk.get("metadata", {}).get("chunk_index", 0)
                })

            return {
                "query": query,
                "n_chunks_found": data.get("n_chunks_found", 0),
                "chunks": chunks,
                "sources": data.get("sources", [])
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in search_documents: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Search failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in search_documents: {e}")
            raise

    async def list_files(
        self,
        user_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """List files accessible to user via main API.

        Args:
            user_id: User ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with file list
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            # Call main API's file list endpoint
            response = await self.http_client.get(
                "/files/",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            data = response.json()

            # Main API returns a list of FileOwnershipInfo objects directly
            # Not wrapped in a dict with "files" key
            if isinstance(data, list):
                files = data
            else:
                # Fallback for older API format
                files = data.get("files", [])

            return {
                "file_count": len(files),
                "files": [
                    {
                        "filename": f.get("filename"),
                        "size_bytes": f.get("file_size") or f.get("size_bytes"),  # API uses "file_size"
                        "uploaded_at": f.get("uploaded_at"),
                        "is_public": f.get("is_public", False),
                        "chunk_count": f.get("chunk_count", 0)
                    }
                    for f in files
                ]
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in list_files: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"List files failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in list_files: {e}")
            raise

    async def get_file_info(
        self,
        filename: str,
        user_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Get file information via main API.

        Args:
            filename: Filename
            user_id: User ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with file info
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            # Call main API's file info endpoint
            response = await self.http_client.get(
                f"/files/{filename}",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            file_metadata = response.json()

            return {
                "filename": file_metadata.get("filename"),
                "size_bytes": file_metadata.get("size_bytes"),
                "uploaded_at": file_metadata.get("uploaded_at"),
                "is_public": file_metadata.get("is_public", False),
                "chunk_count": file_metadata.get("chunk_count", 0),
                "total_uses": file_metadata.get("total_uses", 0),
                "total_views": file_metadata.get("total_views", 0)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_file_info: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                raise ValueError(f"File '{filename}' not found or not accessible")
            raise ValueError(f"Get file info failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_file_info: {e}")
            raise

    async def list_conversations(
        self,
        limit: int,
        user_id: str,
        user_auth0_id: str
    ) -> Dict[str, Any]:
        """List user conversations via main API.

        Args:
            limit: Max conversations to return
            user_id: User ID
            user_auth0_id: User Auth0 ID

        Returns:
            Dict with conversation list
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            # Call main API's conversations endpoint
            response = await self.http_client.get(
                f"/conversations/?limit={limit}",
                headers=self._create_auth_header(user_auth0_id, "student")  # Role doesn't matter for own conversations
            )

            response.raise_for_status()
            data = response.json()

            conversations = data.get("conversations", [])
            return {
                "conversation_count": len(conversations),
                "conversations": [
                    {
                        "conversation_id": conv.get("id") or conv.get("_id"),
                        "title": conv.get("title"),
                        "message_count": conv.get("message_count", 0),
                        "updated_at": conv.get("updated_at")
                    }
                    for conv in conversations
                ]
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in list_conversations: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"List conversations failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in list_conversations: {e}")
            raise

    async def get_user_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user statistics via main API.

        Args:
            user_id: User ID

        Returns:
            Dict with user stats
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            # Call main API's user stats endpoint
            response = await self.http_client.get(
                "/users/me",
                headers={"X-User-ID": user_id}
            )

            response.raise_for_status()
            user_data = response.json()

            return {
                "upload_count": user_data.get("upload_count", 0),
                "query_count": user_data.get("query_count", 0),
                "storage_bytes": user_data.get("storage_bytes", 0),
                "last_activity": user_data.get("last_activity")
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_user_stats: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Get user stats failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_user_stats: {e}")
            raise

    async def delete_file(
        self,
        filename: str,
        user_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Delete a file via main API.

        Args:
            filename: Filename to delete
            user_id: User ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with deletion result
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            # Call main API's file delete endpoint
            response = await self.http_client.delete(
                f"/files/{filename}",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()

            return {
                "success": True,
                "filename": filename,
                "message": f"File '{filename}' deleted successfully"
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in delete_file: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Delete file failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in delete_file: {e}")
            raise

    async def read_file_content(
        self,
        filename: str,
        user_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Read full content of a file via main API.

        Args:
            filename: Filename to read
            user_id: User ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with file content
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            logger.info(f"Reading file content: {filename} for user {user_auth0_id}")

            # Call main API's file content endpoint
            response = await self.http_client.get(
                f"/files/{filename}/content",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            data = response.json()

            return {
                "filename": filename,
                "content": data.get("content", ""),
                "file_size": data.get("file_size", 0),
                "chunk_count": data.get("chunk_count", 0)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in read_file_content: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                raise ValueError(f"File '{filename}' not found or not accessible")
            raise ValueError(f"Read file content failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in read_file_content: {e}")
            raise

    async def web_search(
        self,
        query: str,
        max_results: int,
        user_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Perform web search using DuckDuckGo.

        This tool doesn't need main API - it's independent functionality.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            user_id: User ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with search results
        """
        try:
            logger.info(f"Web search by {user_auth0_id}: '{query}' (max_results={max_results})")

            # Perform DuckDuckGo search
            try:
                # Use DDGS with timeout and region settings
                with DDGS(timeout=20) as ddgs:
                    # Try text search with region parameter
                    search_results = list(ddgs.text(
                        query,
                        max_results=max_results,
                        region='wt-wt',  # Worldwide
                        safesearch='moderate'
                    ))
            except Exception as ddg_error:
                # Handle rate limiting and other DuckDuckGo errors gracefully
                error_msg = str(ddg_error)
                logger.warning(f"DuckDuckGo error for query '{query}': {error_msg}")

                if "Ratelimit" in error_msg or "429" in error_msg or "202" in error_msg:
                    logger.warning(f"DuckDuckGo rate limit hit for query: {query}")
                    # Raise exception so the API returns HTTP 503 and caller can detect the error
                    raise Exception("Search service temporarily unavailable due to rate limiting. Please try again later.")
                else:
                    logger.error(f"DuckDuckGo search error: {ddg_error}", exc_info=True)
                    raise

            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", ""),
                })

            logger.info(f"Web search returned {len(formatted_results)} results")

            return {
                "query": query,
                "results": formatted_results,
                "result_count": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Error in web_search: {e}")
            raise

    # ============================================
    # Academic/University Tool Methods
    # ============================================

    async def get_university_subjects(
        self,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Get all university subjects via main API.

        Args:
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with subjects list
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.get(
                "/academic/subjects",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            subjects = response.json()

            return {
                "subjects": subjects,
                "subject_count": len(subjects)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_university_subjects: {e.response.status_code}")
            raise ValueError(f"Get subjects failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_university_subjects: {e}")
            raise

    async def get_degree_curriculum(
        self,
        degree_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Get degree curriculum via main API.

        Args:
            degree_id: Degree ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with curriculum
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.get(
                f"/academic/degrees/{degree_id}/curriculum",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            data = response.json()

            return {
                "degree_id": data["degree_id"],
                "degree_name": data["degree_name"],
                "curriculum": data["curriculum"]
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_degree_curriculum: {e.response.status_code}")
            raise ValueError(f"Get curriculum failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_degree_curriculum: {e}")
            raise

    async def get_degree_subjects(
        self,
        degree_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Get subjects for a specific degree via main API.

        Args:
            degree_id: Degree ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with subjects list
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.get(
                f"/academic/degrees/{degree_id}/subjects",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            subjects = response.json()

            # Get degree info
            degree_response = await self.http_client.get(
                f"/academic/degrees/{degree_id}",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )
            degree_response.raise_for_status()
            degree_data = degree_response.json()

            return {
                "degree_id": degree_id,
                "degree_name": degree_data.get("degree_name", "Unknown"),
                "subjects": subjects,
                "subject_count": len(subjects)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_degree_subjects: {e.response.status_code}")
            raise ValueError(f"Get degree subjects failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_degree_subjects: {e}")
            raise

    async def upload_student_schooling(
        self,
        degree_id: str,
        schooling_data: List[Dict[str, Any]],
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Upload student schooling records via main API.

        Args:
            degree_id: Degree ID
            schooling_data: List of completed subjects
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with upload result
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.post(
                f"/academic/students/me/schooling/{degree_id}/upload",
                json=schooling_data,
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            result = response.json()

            return {
                "student_id": result.get("student_id"),
                "records_updated": len(schooling_data)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in upload_student_schooling: {e.response.status_code}")
            raise ValueError(f"Upload schooling failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in upload_student_schooling: {e}")
            raise

    async def get_student_schooling(
        self,
        degree_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Get student schooling records via main API.

        Args:
            degree_id: Degree ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with schooling records
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.get(
                f"/academic/students/me/schooling/{degree_id}",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            schooling = response.json()

            # DEBUG: Log what we got from main API
            logger.info(f"DEBUG AGENT_API get_student_schooling: Main API response keys: {schooling.keys()}")
            logger.info(f"DEBUG AGENT_API get_student_schooling: completed_subjects count: {len(schooling.get('completed_subjects', []))}")
            logger.info(f"DEBUG AGENT_API get_student_schooling: in_progress_subjects count: {len(schooling.get('in_progress_subjects', []))}")
            logger.info(f"DEBUG AGENT_API get_student_schooling: in_progress_subjects data: {schooling.get('in_progress_subjects', [])}")

            return {
                "student_id": schooling["student_id"],
                "degree_id": schooling["degree_id"],
                "schooling_records": schooling["completed_subjects"],
                "in_progress_subjects": schooling.get("in_progress_subjects", []),
                "total_credits": schooling["total_credits_earned"],
                "gpa": schooling["gpa"]
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_student_schooling: {e.response.status_code}")
            raise ValueError(f"Get schooling failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_student_schooling: {e}")
            raise

    async def get_student_plan(
        self,
        degree_id: str,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Get student career plan via main API.

        Args:
            degree_id: Degree ID
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with career plan
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.get(
                f"/academic/students/me/plan/{degree_id}",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            plan = response.json()

            return {
                "student_id": plan["student_id"],
                "degree_id": plan["degree_id"],
                "plan": plan["semester_plans"],
                "total_semesters": len(plan["semester_plans"])
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_student_plan: {e.response.status_code}")
            raise ValueError(f"Get plan failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_student_plan: {e}")
            raise

    async def get_student_degree(
        self,
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Get student's enrolled or inferred degree via main API.

        Args:
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with degree_id
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.get(
                "/academic/students/me/degree",
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            data = response.json()

            return {
                "degree_id": data["degree_id"]
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in get_student_degree: {e.response.status_code}")
            raise ValueError(f"Get student degree failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in get_student_degree: {e}")
            raise

    async def update_student_plan(
        self,
        degree_id: str,
        plan_data: Dict[str, Any],
        user_auth0_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """Update student career plan via main API.

        Args:
            degree_id: Degree ID
            plan_data: Updated plan data
            user_auth0_id: User Auth0 ID
            user_role: User role

        Returns:
            Dict with update result
        """
        try:
            if not self.http_client:
                raise RuntimeError("HTTP client not initialized")

            response = await self.http_client.patch(
                f"/academic/students/me/plan/{degree_id}",
                json=plan_data,
                headers=self._create_auth_header(user_auth0_id, user_role)
            )

            response.raise_for_status()
            result = response.json()

            return {
                "student_id": result.get("student_id"),
                "degree_id": result.get("degree_id"),
                "plan_updated": result.get("success", True)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in update_student_plan: {e.response.status_code}")
            raise ValueError(f"Update plan failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Error in update_student_plan: {e}")
            raise


# Global service instance
agent_tool_service = AgentToolService()

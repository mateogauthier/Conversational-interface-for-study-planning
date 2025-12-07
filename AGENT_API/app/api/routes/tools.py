"""Agent tool execution endpoints."""

import logging
from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import (
    SearchDocumentsRequest, SearchDocumentsResponse,
    ListFilesRequest, ListFilesResponse,
    GetFileInfoRequest, GetFileInfoResponse,
    ListConversationsRequest, ListConversationsResponse,
    GetUserStatsRequest, GetUserStatsResponse,
    DeleteFileRequest, DeleteFileResponse,
    WebSearchRequest, WebSearchResponse,
    ReadFileContentRequest, ReadFileContentResponse,
    ToolListResponse,
    # University/Academic endpoints
    GetUniversitySubjectsRequest, GetUniversitySubjectsResponse,
    GetDegreeCurriculumRequest, GetDegreeCurriculumResponse,
    GetDegreeSubjectsRequest, GetDegreeSubjectsResponse,
    UploadStudentSchoolingRequest, UploadStudentSchoolingResponse,
    GetStudentSchoolingRequest, GetStudentSchoolingResponse,
    GetStudentPlanRequest, GetStudentPlanResponse,
    UpdateStudentPlanRequest, UpdateStudentPlanResponse
)
from app.services.tool_services import agent_tool_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/search_documents", response_model=SearchDocumentsResponse)
async def search_documents(request: SearchDocumentsRequest):
    """Search documents using semantic search."""
    try:
        result = await agent_tool_service.search_documents(
            query=request.query,
            n_results=request.n_results,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return SearchDocumentsResponse(
            success=True,
            message="Search completed successfully",
            **result
        )

    except Exception as e:
        logger.error(f"Search documents error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list_files", response_model=ListFilesResponse)
async def list_files(request: ListFilesRequest):
    """List files accessible to the user."""
    try:
        result = await agent_tool_service.list_files(
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return ListFilesResponse(
            success=True,
            message="Files retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"List files error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_file_info", response_model=GetFileInfoResponse)
async def get_file_info(request: GetFileInfoRequest):
    """Get detailed information about a file."""
    try:
        result = await agent_tool_service.get_file_info(
            filename=request.filename,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return GetFileInfoResponse(
            success=True,
            message="File info retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"Get file info error: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/list_conversations", response_model=ListConversationsResponse)
async def list_conversations(request: ListConversationsRequest):
    """List user's conversations."""
    try:
        result = await agent_tool_service.list_conversations(
            limit=request.limit,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id
        )

        return ListConversationsResponse(
            success=True,
            message="Conversations retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"List conversations error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_user_stats", response_model=GetUserStatsResponse)
async def get_user_stats(request: GetUserStatsRequest):
    """Get user statistics."""
    try:
        result = await agent_tool_service.get_user_stats(
            user_id=request.user_id
        )

        return GetUserStatsResponse(
            success=True,
            message="User stats retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"Get user stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete_file", response_model=DeleteFileResponse)
async def delete_file(request: DeleteFileRequest):
    """Delete a file (requires confirmation in agent flow)."""
    try:
        result = await agent_tool_service.delete_file(
            filename=request.filename,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return DeleteFileResponse(
            success=True,
            message=result["message"],
            filename=result["filename"]
        )

    except Exception as e:
        logger.error(f"Delete file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web_search", response_model=WebSearchResponse)
async def web_search(request: WebSearchRequest):
    """Perform web search using DuckDuckGo."""
    try:
        result = await agent_tool_service.web_search(
            query=request.query,
            max_results=request.max_results,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return WebSearchResponse(
            success=True,
            message="Web search completed successfully",
            **result
        )

    except Exception as e:
        error_msg = str(e)
        # Return 503 for rate limiting, 500 for other errors
        if "rate limiting" in error_msg.lower() or "ratelimit" in error_msg.lower():
            logger.warning(f"Web search rate limited: {e}")
            raise HTTPException(status_code=503, detail=error_msg)
        else:
            logger.error(f"Web search error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)


@router.post("/read_file_content", response_model=ReadFileContentResponse)
async def read_file_content(request: ReadFileContentRequest):
    """Read full content of a specific file."""
    try:
        result = await agent_tool_service.read_file_content(
            filename=request.filename,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return ReadFileContentResponse(
            success=True,
            message=f"File content retrieved successfully",
            **result
        )

    except ValueError as e:
        logger.error(f"Read file content error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Read file content error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# University/Academic Tool Endpoints
# ============================================

@router.post("/get_university_subjects", response_model=GetUniversitySubjectsResponse)
async def get_university_subjects(request: GetUniversitySubjectsRequest):
    """Get all university subjects.

    PLACEHOLDER: This endpoint returns hardcoded data.
    TODO: Implement actual integration with university API/database.
    """
    try:
        # PLACEHOLDER: Return hardcoded sample data
        placeholder_subjects = [
            {
                "subject_id": "MAT101",
                "name": "Calculus I",
                "credits": 8,
                "department": "Mathematics"
            },
            {
                "subject_id": "PROG101",
                "name": "Programming I",
                "credits": 8,
                "department": "Computer Science"
            },
            {
                "subject_id": "FIS101",
                "name": "Physics I",
                "credits": 6,
                "department": "Physics"
            }
        ]

        logger.info(f"[PLACEHOLDER] Returning {len(placeholder_subjects)} hardcoded subjects")

        return GetUniversitySubjectsResponse(
            success=True,
            message="[PLACEHOLDER] University subjects retrieved (hardcoded data)",
            subjects=placeholder_subjects,
            subject_count=len(placeholder_subjects)
        )

    except Exception as e:
        logger.error(f"Get university subjects error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_degree_curriculum", response_model=GetDegreeCurriculumResponse)
async def get_degree_curriculum(request: GetDegreeCurriculumRequest):
    """Get suggested curriculum for a specific degree.

    PLACEHOLDER: This endpoint returns hardcoded data.
    TODO: Implement actual integration with university API/database.
    """
    try:
        # PLACEHOLDER: Return hardcoded curriculum
        placeholder_curriculum = [
            {
                "semester": 1,
                "subjects": [
                    {"subject_id": "MAT101", "name": "Calculus I", "credits": 8},
                    {"subject_id": "PROG101", "name": "Programming I", "credits": 8}
                ]
            },
            {
                "semester": 2,
                "subjects": [
                    {"subject_id": "MAT102", "name": "Calculus II", "credits": 8},
                    {"subject_id": "PROG102", "name": "Programming II", "credits": 8}
                ]
            }
        ]

        logger.info(f"[PLACEHOLDER] Returning hardcoded curriculum for degree: {request.degree_id}")

        return GetDegreeCurriculumResponse(
            success=True,
            message=f"[PLACEHOLDER] Curriculum retrieved for {request.degree_id} (hardcoded data)",
            degree_id=request.degree_id,
            degree_name="[PLACEHOLDER] Computer Engineering",
            curriculum=placeholder_curriculum
        )

    except Exception as e:
        logger.error(f"Get degree curriculum error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_degree_subjects", response_model=GetDegreeSubjectsResponse)
async def get_degree_subjects(request: GetDegreeSubjectsRequest):
    """Get subjects and prerequisites for a specific degree.

    PLACEHOLDER: This endpoint returns hardcoded data.
    TODO: Implement actual integration with university API/database.
    """
    try:
        # PLACEHOLDER: Return hardcoded subjects with prerequisites
        placeholder_subjects = [
            {
                "subject_id": "MAT101",
                "name": "Calculus I",
                "credits": 8,
                "prerequisites": []
            },
            {
                "subject_id": "MAT102",
                "name": "Calculus II",
                "credits": 8,
                "prerequisites": ["MAT101"]
            },
            {
                "subject_id": "PROG101",
                "name": "Programming I",
                "credits": 8,
                "prerequisites": []
            },
            {
                "subject_id": "PROG102",
                "name": "Programming II",
                "credits": 8,
                "prerequisites": ["PROG101"]
            }
        ]

        logger.info(f"[PLACEHOLDER] Returning hardcoded subjects for degree: {request.degree_id}")

        return GetDegreeSubjectsResponse(
            success=True,
            message=f"[PLACEHOLDER] Subjects retrieved for {request.degree_id} (hardcoded data)",
            degree_id=request.degree_id,
            degree_name="[PLACEHOLDER] Computer Engineering",
            subjects=placeholder_subjects,
            subject_count=len(placeholder_subjects)
        )

    except Exception as e:
        logger.error(f"Get degree subjects error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_student_schooling", response_model=UploadStudentSchoolingResponse)
async def upload_student_schooling(request: UploadStudentSchoolingRequest):
    """Upload/update student's schooling records.

    PLACEHOLDER: This endpoint simulates data upload.
    TODO: Implement actual database persistence.
    """
    try:
        # PLACEHOLDER: Simulate uploading data
        logger.info(f"[PLACEHOLDER] Would upload schooling data for student: {request.student_id}")
        logger.info(f"[PLACEHOLDER] Data received: {request.schooling_data}")

        # Count how many records were "uploaded"
        records_count = len(request.schooling_data) if isinstance(request.schooling_data, list) else 1

        return UploadStudentSchoolingResponse(
            success=True,
            message=f"[PLACEHOLDER] Schooling data uploaded for {request.student_id} (not persisted)",
            student_id=request.student_id,
            records_updated=records_count
        )

    except Exception as e:
        logger.error(f"Upload student schooling error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_student_schooling", response_model=GetStudentSchoolingResponse)
async def get_student_schooling(request: GetStudentSchoolingRequest):
    """Get student's schooling records for a specific degree.

    PLACEHOLDER: This endpoint returns hardcoded data.
    TODO: Implement actual database query.
    """
    try:
        # PLACEHOLDER: Return hardcoded schooling records
        placeholder_records = [
            {
                "subject_id": "MAT101",
                "subject_name": "Calculus I",
                "grade": 85,
                "credits": 8,
                "semester": "2023-1",
                "status": "Passed"
            },
            {
                "subject_id": "PROG101",
                "subject_name": "Programming I",
                "grade": 92,
                "credits": 8,
                "semester": "2023-1",
                "status": "Passed"
            },
            {
                "subject_id": "MAT102",
                "subject_name": "Calculus II",
                "grade": 78,
                "credits": 8,
                "semester": "2023-2",
                "status": "Passed"
            }
        ]

        # PLACEHOLDER: Calculate fake GPA
        total_credits = sum(r["credits"] for r in placeholder_records)
        weighted_sum = sum(r["grade"] * r["credits"] for r in placeholder_records)
        gpa = weighted_sum / total_credits if total_credits > 0 else 0.0

        logger.info(f"[PLACEHOLDER] Returning hardcoded schooling for student: {request.student_id}")

        return GetStudentSchoolingResponse(
            success=True,
            message=f"[PLACEHOLDER] Schooling records retrieved for {request.student_id} (hardcoded data)",
            student_id=request.student_id,
            degree_id=request.degree_id,
            schooling_records=placeholder_records,
            total_credits=total_credits,
            gpa=round(gpa, 2)
        )

    except Exception as e:
        logger.error(f"Get student schooling error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_student_plan", response_model=GetStudentPlanResponse)
async def get_student_plan(request: GetStudentPlanRequest):
    """Get student's career plan.

    PLACEHOLDER: This endpoint returns hardcoded data.
    TODO: Implement actual database query.
    """
    try:
        # PLACEHOLDER: Return hardcoded career plan
        placeholder_plan = [
            {
                "semester": "2024-1",
                "planned_subjects": [
                    {"subject_id": "PROG102", "subject_name": "Programming II", "credits": 8},
                    {"subject_id": "DB101", "subject_name": "Database Systems I", "credits": 8}
                ]
            },
            {
                "semester": "2024-2",
                "planned_subjects": [
                    {"subject_id": "PROG103", "subject_name": "Programming III", "credits": 8},
                    {"subject_id": "DB102", "subject_name": "Database Systems II", "credits": 8}
                ]
            }
        ]

        logger.info(f"[PLACEHOLDER] Returning hardcoded plan for student: {request.student_id}")

        return GetStudentPlanResponse(
            success=True,
            message=f"[PLACEHOLDER] Career plan retrieved for {request.student_id} (hardcoded data)",
            student_id=request.student_id,
            degree_id=request.degree_id,
            plan=placeholder_plan,
            total_semesters=len(placeholder_plan)
        )

    except Exception as e:
        logger.error(f"Get student plan error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/update_student_plan", response_model=UpdateStudentPlanResponse)
async def update_student_plan(request: UpdateStudentPlanRequest):
    """Modify student's career plan.

    PLACEHOLDER: This endpoint simulates plan modification.
    TODO: Implement actual database update.
    """
    try:
        # PLACEHOLDER: Simulate updating plan
        logger.info(f"[PLACEHOLDER] Would update plan for student: {request.student_id}")
        logger.info(f"[PLACEHOLDER] Plan data received: {request.plan_data}")

        return UpdateStudentPlanResponse(
            success=True,
            message=f"[PLACEHOLDER] Career plan updated for {request.student_id} (not persisted)",
            student_id=request.student_id,
            degree_id=request.degree_id,
            plan_updated=True  # PLACEHOLDER: Always return true
        )

    except Exception as e:
        logger.error(f"Update student plan error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Tool Discovery Endpoint
# ============================================

@router.get("/list", response_model=ToolListResponse)
async def list_available_tools():
    """List all available agent tools."""
    tools = [
        {
            "name": "search_documents",
            "description": "Search through documents using semantic search",
            "endpoint": "/tools/search_documents",
            "method": "POST",
            "parameters": ["query", "n_results", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "list_files",
            "description": "List all files accessible to the user",
            "endpoint": "/tools/list_files",
            "method": "POST",
            "parameters": ["user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "get_file_info",
            "description": "Get detailed information about a specific file",
            "endpoint": "/tools/get_file_info",
            "method": "POST",
            "parameters": ["filename", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "list_conversations",
            "description": "List user's conversation history",
            "endpoint": "/tools/list_conversations",
            "method": "POST",
            "parameters": ["limit", "user_id", "user_auth0_id"]
        },
        {
            "name": "get_user_stats",
            "description": "Get user's usage statistics",
            "endpoint": "/tools/get_user_stats",
            "method": "POST",
            "parameters": ["user_id"]
        },
        {
            "name": "delete_file",
            "description": "Delete a file (requires confirmation)",
            "endpoint": "/tools/delete_file",
            "method": "POST",
            "parameters": ["filename", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo",
            "endpoint": "/tools/web_search",
            "method": "POST",
            "parameters": ["query", "max_results", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "read_file_content",
            "description": "Read full text content of a specific file",
            "endpoint": "/tools/read_file_content",
            "method": "POST",
            "parameters": ["filename", "user_id", "user_auth0_id", "user_role"]
        },
        # University/Academic tools (PLACEHOLDER implementations)
        {
            "name": "get_university_subjects",
            "description": "[PLACEHOLDER] Get all available university subjects",
            "endpoint": "/tools/get_university_subjects",
            "method": "POST",
            "parameters": ["user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "get_degree_curriculum",
            "description": "[PLACEHOLDER] Get suggested curriculum for a specific degree",
            "endpoint": "/tools/get_degree_curriculum",
            "method": "POST",
            "parameters": ["degree_id", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "get_degree_subjects",
            "description": "[PLACEHOLDER] Get subjects and prerequisites for a degree",
            "endpoint": "/tools/get_degree_subjects",
            "method": "POST",
            "parameters": ["degree_id", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "upload_student_schooling",
            "description": "[PLACEHOLDER] Upload/update student's academic records",
            "endpoint": "/tools/upload_student_schooling",
            "method": "POST",
            "parameters": ["student_id", "schooling_data", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "get_student_schooling",
            "description": "[PLACEHOLDER] Get student's completed subjects and grades",
            "endpoint": "/tools/get_student_schooling",
            "method": "POST",
            "parameters": ["student_id", "degree_id", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "get_student_plan",
            "description": "[PLACEHOLDER] Get student's career/study plan",
            "endpoint": "/tools/get_student_plan",
            "method": "POST",
            "parameters": ["student_id", "degree_id", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "update_student_plan",
            "description": "[PLACEHOLDER] Modify student's career/study plan",
            "endpoint": "/tools/update_student_plan",
            "method": "PATCH",
            "parameters": ["student_id", "degree_id", "plan_data", "user_id", "user_auth0_id", "user_role"]
        }
    ]

    return ToolListResponse(
        success=True,
        message="Available tools retrieved",
        tools=tools,
        tool_count=len(tools)
    )

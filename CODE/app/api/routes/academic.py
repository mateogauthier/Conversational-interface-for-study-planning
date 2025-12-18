"""Academic system routes for degrees, subjects, and student progress."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.services.academic_service import get_academic_service
from app.db.models import UserInDB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/academic", tags=["academic"])


# ============================================
# Request/Response Models
# ============================================

class DegreeResponse(BaseModel):
    """Response model for degree information."""
    degree_id: str
    degree_name: str
    university: str
    total_credits: int
    duration_semesters: int
    description: str | None = None
    department: str | None = None


class SubjectResponse(BaseModel):
    """Response model for subject information."""
    subject_id: str
    name: str
    credits: int
    department: str | None = None
    description: str | None = None
    prerequisites: List[str] = Field(default_factory=list)
    semester_offered: int | None = None


class DegreeSubjectResponse(BaseModel):
    """Response model for degree subject with full details."""
    subject_id: str
    name: str
    credits: int
    department: str | None = None
    description: str | None = None
    prerequisites: List[str] = Field(default_factory=list)
    corequisites: List[str] = Field(default_factory=list)
    semester_offered: int
    is_elective: bool = False


class StudentSchoolingResponse(BaseModel):
    """Response model for student transcript."""
    student_id: str
    degree_id: str
    enrollment_date: str
    current_semester: str | None = None
    academic_status: str
    completed_subjects: List[Dict[str, Any]] = Field(default_factory=list)
    in_progress_subjects: List[Dict[str, Any]] = Field(default_factory=list)
    total_credits_earned: int
    total_credits_attempted: int
    gpa: float


class StudentPlanResponse(BaseModel):
    """Response model for student's study plan."""
    student_id: str
    degree_id: str
    plan_name: str | None = None
    semester_plans: List[Dict[str, Any]] = Field(default_factory=list)
    target_graduation: str | None = None


# ============================================
# Degree Endpoints
# ============================================

@router.get("/degrees", response_model=List[DegreeResponse])
async def list_degrees(
    current_user: UserInDB = Depends(get_current_user)
):
    """List all available degree programs."""
    try:
        academic_service = get_academic_service()
        degrees = await academic_service.list_degrees()

        return [
            DegreeResponse(
                degree_id=d.degree_id,
                degree_name=d.degree_name,
                university=d.university,
                total_credits=d.total_credits,
                duration_semesters=d.duration_semesters,
                description=d.description,
                department=d.department
            )
            for d in degrees
        ]

    except Exception as e:
        logger.error(f"Error listing degrees: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/degrees/{degree_id}", response_model=DegreeResponse)
async def get_degree(
    degree_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get details of a specific degree program."""
    try:
        academic_service = get_academic_service()
        degree = await academic_service.get_degree(degree_id)

        if not degree:
            raise HTTPException(status_code=404, detail=f"Degree {degree_id} not found")

        return DegreeResponse(
            degree_id=degree.degree_id,
            degree_name=degree.degree_name,
            university=degree.university,
            total_credits=degree.total_credits,
            duration_semesters=degree.duration_semesters,
            description=degree.description,
            department=degree.department
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting degree {degree_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/degrees/{degree_id}/curriculum")
async def get_degree_curriculum(
    degree_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get suggested curriculum for a degree, organized by semester."""
    try:
        academic_service = get_academic_service()

        # Verify degree exists
        degree = await academic_service.get_degree(degree_id)
        if not degree:
            raise HTTPException(status_code=404, detail=f"Degree {degree_id} not found")

        curriculum = await academic_service.get_degree_curriculum(degree_id)

        return {
            "degree_id": degree_id,
            "degree_name": degree.degree_name,
            "curriculum": curriculum
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting curriculum for {degree_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Subject Endpoints
# ============================================

@router.get("/subjects", response_model=List[SubjectResponse])
async def list_all_subjects(
    current_user: UserInDB = Depends(get_current_user)
):
    """List all subjects across all degrees (university-wide)."""
    try:
        academic_service = get_academic_service()
        subjects = await academic_service.get_all_subjects()

        return [
            SubjectResponse(**s)
            for s in subjects
        ]

    except Exception as e:
        logger.error(f"Error listing all subjects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/degrees/{degree_id}/subjects", response_model=List[DegreeSubjectResponse])
async def list_degree_subjects(
    degree_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """List all subjects for a specific degree with prerequisites."""
    try:
        academic_service = get_academic_service()

        # Verify degree exists
        degree = await academic_service.get_degree(degree_id)
        if not degree:
            raise HTTPException(status_code=404, detail=f"Degree {degree_id} not found")

        subjects = await academic_service.get_degree_subjects(degree_id)

        return [
            DegreeSubjectResponse(
                subject_id=s.subject_id,
                name=s.name,
                credits=s.credits,
                department=s.department,
                description=s.description,
                prerequisites=s.prerequisites,
                corequisites=s.corequisites,
                semester_offered=s.semester_offered,
                is_elective=s.is_elective
            )
            for s in subjects
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing subjects for {degree_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Student Schooling (Transcript) Endpoints
# ============================================

@router.get("/students/me/schooling/{degree_id}", response_model=StudentSchoolingResponse)
async def get_my_schooling(
    degree_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get current user's transcript for a specific degree."""
    try:
        academic_service = get_academic_service()

        # Get or create schooling record
        schooling = await academic_service.get_or_create_student_schooling(
            student_id=current_user.auth0_id,
            degree_id=degree_id,
            user_id=str(current_user.id)
        )

        return StudentSchoolingResponse(
            student_id=schooling.student_id,
            degree_id=schooling.degree_id,
            enrollment_date=schooling.enrollment_date.isoformat(),
            current_semester=schooling.current_semester,
            academic_status=schooling.academic_status,
            completed_subjects=[
                {
                    "subject_id": s.subject_id,
                    "subject_name": s.subject_name,
                    "credits": s.credits,
                    "grade": s.grade,
                    "letter_grade": s.letter_grade,
                    "status": s.status,
                    "semester": s.semester,
                    "attempt_number": s.attempt_number
                }
                for s in schooling.completed_subjects
            ],
            in_progress_subjects=[
                {
                    "subject_id": s.subject_id,
                    "subject_name": s.subject_name,
                    "credits": s.credits,
                    "status": s.status,
                    "semester": s.semester
                }
                for s in schooling.in_progress_subjects
            ],
            total_credits_earned=schooling.total_credits_earned,
            total_credits_attempted=schooling.total_credits_attempted,
            gpa=schooling.gpa
        )

    except Exception as e:
        logger.error(f"Error getting schooling: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/students/me/schooling/{degree_id}/upload")
async def upload_my_schooling(
    degree_id: str,
    subjects: List[Dict[str, Any]],
    current_user: UserInDB = Depends(get_current_user)
):
    """Bulk upload completed subjects to transcript."""
    try:
        academic_service = get_academic_service()

        # Verify degree exists
        degree = await academic_service.get_degree(degree_id)
        if not degree:
            raise HTTPException(status_code=404, detail=f"Degree {degree_id} not found")

        # Upload schooling data
        schooling = await academic_service.bulk_upload_schooling(
            student_id=current_user.auth0_id,
            degree_id=degree_id,
            user_id=str(current_user.id),
            subjects=subjects
        )

        return {
            "success": True,
            "message": f"Uploaded {len(subjects)} subject records",
            "student_id": schooling.student_id,
            "degree_id": schooling.degree_id,
            "total_credits_earned": schooling.total_credits_earned,
            "gpa": schooling.gpa
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading schooling: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Student Plan Endpoints
# ============================================

@router.get("/students/me/plan/{degree_id}", response_model=StudentPlanResponse)
async def get_my_plan(
    degree_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """Get current user's study plan for a specific degree."""
    try:
        academic_service = get_academic_service()

        # Get or create plan
        plan = await academic_service.get_or_create_student_plan(
            student_id=current_user.auth0_id,
            degree_id=degree_id,
            user_id=str(current_user.id)
        )

        return StudentPlanResponse(
            student_id=plan.student_id,
            degree_id=plan.degree_id,
            plan_name=plan.plan_name,
            semester_plans=[
                {
                    "semester": sp.semester,
                    "planned_subjects": [
                        {
                            "subject_id": ps.subject_id,
                            "subject_name": ps.subject_name,
                            "credits": ps.credits,
                            "priority": ps.priority,
                            "notes": ps.notes
                        }
                        for ps in sp.planned_subjects
                    ],
                    "total_credits": sp.total_credits,
                    "notes": sp.notes
                }
                for sp in plan.semester_plans
            ],
            target_graduation=plan.target_graduation.isoformat() if plan.target_graduation else None
        )

    except Exception as e:
        logger.error(f"Error getting plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/students/me/plan/{degree_id}")
async def update_my_plan(
    degree_id: str,
    plan_data: Dict[str, Any],
    current_user: UserInDB = Depends(get_current_user)
):
    """Update current user's study plan."""
    try:
        academic_service = get_academic_service()

        # Verify degree exists
        degree = await academic_service.get_degree(degree_id)
        if not degree:
            raise HTTPException(status_code=404, detail=f"Degree {degree_id} not found")

        # Update plan
        plan = await academic_service.update_student_plan(
            student_id=current_user.auth0_id,
            degree_id=degree_id,
            plan_data=plan_data
        )

        if not plan:
            raise HTTPException(status_code=404, detail="Student plan not found")

        return {
            "success": True,
            "message": "Study plan updated successfully",
            "student_id": plan.student_id,
            "degree_id": plan.degree_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

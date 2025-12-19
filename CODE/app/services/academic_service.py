"""Academic system service for managing degrees, subjects, and student progress."""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.models import (
    DegreeInDB,
    DegreeSubjectInDB,
    StudentSchoolingInDB,
    StudentSubjectRecord,
    StudentPlanInDB,
    SemesterPlan,
    PlannedSubject
)

logger = logging.getLogger(__name__)


class AcademicService:
    """Service for academic operations (degrees, subjects, transcripts, plans)."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize academic service with database connection."""
        self.db = db
        self.degrees_collection = db.degrees
        self.degree_subjects_collection = db.degree_subjects
        self.student_schooling_collection = db.student_schooling
        self.student_plans_collection = db.student_plans

    # ============================================
    # Degree Operations
    # ============================================

    async def create_degree(self, degree_data: Dict[str, Any]) -> DegreeInDB:
        """Create a new degree program."""
        degree = DegreeInDB(**degree_data)
        result = await self.degrees_collection.insert_one(degree.model_dump(by_alias=True, exclude={"id"}))
        degree.id = result.inserted_id
        logger.info(f"Created degree: {degree.degree_id}")
        return degree

    async def get_degree(self, degree_id: str) -> Optional[DegreeInDB]:
        """Get degree by degree_id."""
        degree_doc = await self.degrees_collection.find_one({"degree_id": degree_id})
        if not degree_doc:
            return None
        return DegreeInDB(**degree_doc)

    async def list_degrees(self) -> List[DegreeInDB]:
        """List all degree programs."""
        cursor = self.degrees_collection.find({})
        degrees = []
        async for doc in cursor:
            degrees.append(DegreeInDB(**doc))
        return degrees

    async def update_degree(self, degree_id: str, update_data: Dict[str, Any]) -> Optional[DegreeInDB]:
        """Update degree information."""
        update_data["updated_at"] = datetime.utcnow()
        result = await self.degrees_collection.update_one(
            {"degree_id": degree_id},
            {"$set": update_data}
        )
        if result.matched_count == 0:
            return None
        return await self.get_degree(degree_id)

    async def delete_degree(self, degree_id: str) -> bool:
        """Delete a degree program."""
        result = await self.degrees_collection.delete_one({"degree_id": degree_id})
        return result.deleted_count > 0

    # ============================================
    # Subject Operations
    # ============================================

    async def create_degree_subject(self, subject_data: Dict[str, Any]) -> DegreeSubjectInDB:
        """Add a subject to a degree curriculum."""
        subject = DegreeSubjectInDB(**subject_data)
        result = await self.degree_subjects_collection.insert_one(subject.model_dump(by_alias=True, exclude={"id"}))
        subject.id = result.inserted_id
        logger.info(f"Created subject {subject.subject_id} for degree {subject.degree_id}")
        return subject

    async def get_degree_subjects(self, degree_id: str) -> List[DegreeSubjectInDB]:
        """Get all subjects for a specific degree."""
        cursor = self.degree_subjects_collection.find({"degree_id": degree_id}).sort("semester_offered", 1)
        subjects = []
        async for doc in cursor:
            subjects.append(DegreeSubjectInDB(**doc))
        return subjects

    async def get_subject(self, degree_id: str, subject_id: str) -> Optional[DegreeSubjectInDB]:
        """Get a specific subject from a degree."""
        subject_doc = await self.degree_subjects_collection.find_one({
            "degree_id": degree_id,
            "subject_id": subject_id
        })
        if not subject_doc:
            return None
        return DegreeSubjectInDB(**subject_doc)

    async def get_all_subjects(self) -> List[Dict[str, Any]]:
        """Get all subjects across all degrees (for university-wide view)."""
        # Aggregate to get unique subjects
        pipeline = [
            {
                "$group": {
                    "_id": "$subject_id",
                    "name": {"$first": "$name"},
                    "credits": {"$first": "$credits"},
                    "department": {"$first": "$department"},
                    "description": {"$first": "$description"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        cursor = self.degree_subjects_collection.aggregate(pipeline)
        subjects = []
        async for doc in cursor:
            subjects.append({
                "subject_id": doc["_id"],
                "name": doc["name"],
                "credits": doc["credits"],
                "department": doc.get("department"),
                "description": doc.get("description")
            })
        return subjects

    async def update_degree_subject(self, degree_id: str, subject_id: str, update_data: Dict[str, Any]) -> Optional[DegreeSubjectInDB]:
        """Update subject information."""
        update_data["updated_at"] = datetime.utcnow()
        result = await self.degree_subjects_collection.update_one(
            {"degree_id": degree_id, "subject_id": subject_id},
            {"$set": update_data}
        )
        if result.matched_count == 0:
            return None
        return await self.get_subject(degree_id, subject_id)

    async def delete_degree_subject(self, degree_id: str, subject_id: str) -> bool:
        """Remove a subject from a degree."""
        result = await self.degree_subjects_collection.delete_one({
            "degree_id": degree_id,
            "subject_id": subject_id
        })
        return result.deleted_count > 0

    async def get_degree_curriculum(self, degree_id: str) -> List[Dict[str, Any]]:
        """Get suggested curriculum organized by semester."""
        subjects = await self.get_degree_subjects(degree_id)

        # Group by semester
        curriculum = {}
        for subject in subjects:
            semester = subject.semester_offered
            if semester not in curriculum:
                curriculum[semester] = []
            curriculum[semester].append({
                "subject_id": subject.subject_id,
                "name": subject.name,
                "credits": subject.credits,
                "prerequisites": subject.prerequisites,
                "is_elective": subject.is_elective
            })

        # Convert to sorted list
        result = []
        for semester in sorted(curriculum.keys()):
            result.append({
                "semester": semester,
                "subjects": curriculum[semester]
            })

        return result

    # ============================================
    # Student Schooling (Transcript) Operations
    # ============================================

    async def create_student_schooling(self, schooling_data: Dict[str, Any]) -> StudentSchoolingInDB:
        """Create a new student schooling record."""
        schooling = StudentSchoolingInDB(**schooling_data)
        result = await self.student_schooling_collection.insert_one(schooling.model_dump(by_alias=True, exclude={"id"}))
        schooling.id = result.inserted_id
        logger.info(f"Created schooling record for student {schooling.student_id} in degree {schooling.degree_id}")
        return schooling

    async def get_student_schooling(self, student_id: str, degree_id: str) -> Optional[StudentSchoolingInDB]:
        """Get student's schooling record for a specific degree."""
        schooling_doc = await self.student_schooling_collection.find_one({
            "student_id": student_id,
            "degree_id": degree_id
        })
        if not schooling_doc:
            return None
        return StudentSchoolingInDB(**schooling_doc)

    async def get_or_create_student_schooling(self, student_id: str, degree_id: str, user_id: str) -> StudentSchoolingInDB:
        """Get student schooling or create if it doesn't exist."""
        schooling = await self.get_student_schooling(student_id, degree_id)
        if not schooling:
            schooling = await self.create_student_schooling({
                "student_id": student_id,
                "degree_id": degree_id,
                "user_id": user_id,
                "academic_status": "Active"
            })
        return schooling

    async def get_student_degrees(self, student_id: str) -> List[str]:
        """Get all degree IDs the student is enrolled in."""
        cursor = self.student_schooling_collection.find(
            {"student_id": student_id},
            {"degree_id": 1}
        )
        degree_ids = []
        async for doc in cursor:
            degree_ids.append(doc["degree_id"])
        return degree_ids

    async def get_or_infer_student_degree(self, student_id: str) -> Optional[str]:
        """
        Get the student's degree ID, or infer it intelligently.

        Strategy:
        1. Check if student has any schooling records - use the first one
        2. If no schooling records, check available degrees and return the first one
        3. If no degrees exist, return None
        """
        # Try to get student's enrolled degrees
        enrolled_degrees = await self.get_student_degrees(student_id)

        if enrolled_degrees:
            # Student has at least one degree - use the first one
            logger.info(f"Found {len(enrolled_degrees)} degree(s) for student {student_id}: {enrolled_degrees}")
            return enrolled_degrees[0]

        # No schooling records - check if any degrees exist in the system
        degrees = await self.list_degrees()
        if degrees:
            # Return the first available degree
            default_degree_id = degrees[0].degree_id
            logger.info(f"No enrollment found for student {student_id}, using first available degree: {default_degree_id}")
            return default_degree_id

        # No degrees at all
        logger.warning(f"No degrees found in the system for student {student_id}")
        return None

    async def add_completed_subject(
        self,
        student_id: str,
        degree_id: str,
        subject_record: Dict[str, Any]
    ) -> Optional[StudentSchoolingInDB]:
        """Add a completed subject to student's transcript.

        Also removes the subject from in_progress_subjects if it exists there,
        to maintain data consistency.
        """
        # Validate subject exists in degree
        subject = await self.get_subject(degree_id, subject_record["subject_id"])
        if not subject:
            logger.warning(f"Subject {subject_record['subject_id']} not found in degree {degree_id}")
            return None

        # Create subject record
        record = StudentSubjectRecord(**subject_record)

        # Update schooling record:
        # 1. Remove from in_progress_subjects (if present)
        # 2. Add to completed_subjects
        result = await self.student_schooling_collection.update_one(
            {"student_id": student_id, "degree_id": degree_id},
            {
                "$pull": {"in_progress_subjects": {"subject_id": record.subject_id}},
                "$push": {"completed_subjects": record.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.matched_count == 0:
            return None

        # Recalculate statistics
        await self._recalculate_student_stats(student_id, degree_id)

        return await self.get_student_schooling(student_id, degree_id)

    async def update_subject_grade(
        self,
        student_id: str,
        degree_id: str,
        subject_id: str,
        semester: str,
        grade: float,
        status: str
    ) -> Optional[StudentSchoolingInDB]:
        """Update a subject's grade in student's transcript."""
        result = await self.student_schooling_collection.update_one(
            {
                "student_id": student_id,
                "degree_id": degree_id,
                "completed_subjects.subject_id": subject_id,
                "completed_subjects.semester": semester
            },
            {
                "$set": {
                    "completed_subjects.$.grade": grade,
                    "completed_subjects.$.status": status,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.matched_count == 0:
            return None

        # Recalculate statistics
        await self._recalculate_student_stats(student_id, degree_id)

        return await self.get_student_schooling(student_id, degree_id)

    async def bulk_upload_schooling(
        self,
        student_id: str,
        degree_id: str,
        user_id: str,
        subjects: List[Dict[str, Any]]
    ) -> StudentSchoolingInDB:
        """Bulk upload student's schooling records."""
        # Get or create schooling record
        schooling = await self.get_or_create_student_schooling(student_id, degree_id, user_id)

        # Validate and add subjects
        records = []
        for subject_data in subjects:
            # Validate subject exists
            subject = await self.get_subject(degree_id, subject_data["subject_id"])
            if subject:
                record = StudentSubjectRecord(**subject_data)
                records.append(record.model_dump())
            else:
                logger.warning(f"Skipping unknown subject: {subject_data['subject_id']}")

        if records:
            # Add all records
            await self.student_schooling_collection.update_one(
                {"student_id": student_id, "degree_id": degree_id},
                {
                    "$push": {"completed_subjects": {"$each": records}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            # Recalculate statistics
            await self._recalculate_student_stats(student_id, degree_id)

        return await self.get_student_schooling(student_id, degree_id)

    async def add_in_progress_subject(
        self,
        student_id: str,
        degree_id: str,
        subject_record: Dict[str, Any]
    ) -> Optional[StudentSchoolingInDB]:
        """Add a subject to student's in-progress list."""
        # Create subject record
        record = StudentSubjectRecord(**subject_record)

        # Update schooling record
        result = await self.student_schooling_collection.update_one(
            {"student_id": student_id, "degree_id": degree_id},
            {
                "$push": {"in_progress_subjects": record.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.matched_count == 0:
            return None

        return await self.get_student_schooling(student_id, degree_id)

    async def remove_subject(
        self,
        student_id: str,
        degree_id: str,
        subject_id: str
    ) -> Optional[StudentSchoolingInDB]:
        """Remove a subject from both completed and in-progress lists."""
        # Remove from both arrays
        result = await self.student_schooling_collection.update_one(
            {"student_id": student_id, "degree_id": degree_id},
            {
                "$pull": {
                    "completed_subjects": {"subject_id": subject_id},
                    "in_progress_subjects": {"subject_id": subject_id}
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.matched_count == 0:
            return None

        # Recalculate statistics after removal
        await self._recalculate_student_stats(student_id, degree_id)

        return await self.get_student_schooling(student_id, degree_id)

    async def get_degree_subject(self, degree_id: str, subject_id: str) -> Optional[DegreeSubjectInDB]:
        """Get a specific subject from a degree."""
        subject_doc = await self.degree_subjects_collection.find_one({
            "degree_id": degree_id,
            "subject_id": subject_id
        })
        if not subject_doc:
            return None
        return DegreeSubjectInDB(**subject_doc)

    async def _recalculate_student_stats(self, student_id: str, degree_id: str) -> None:
        """Recalculate GPA and credit totals for a student."""
        schooling = await self.get_student_schooling(student_id, degree_id)
        if not schooling:
            return

        total_credits_earned = 0
        total_credits_attempted = 0
        weighted_grade_sum = 0.0

        for record in schooling.completed_subjects:
            if record.status == "Passed":
                total_credits_earned += record.credits
                if record.grade is not None:
                    weighted_grade_sum += record.grade * record.credits
            total_credits_attempted += record.credits

        gpa = weighted_grade_sum / total_credits_attempted if total_credits_attempted > 0 else 0.0

        await self.student_schooling_collection.update_one(
            {"student_id": student_id, "degree_id": degree_id},
            {
                "$set": {
                    "total_credits_earned": total_credits_earned,
                    "total_credits_attempted": total_credits_attempted,
                    "gpa": round(gpa, 2),
                    "updated_at": datetime.utcnow()
                }
            }
        )

    # ============================================
    # Student Plan Operations
    # ============================================

    async def create_student_plan(self, plan_data: Dict[str, Any]) -> StudentPlanInDB:
        """Create a new student plan."""
        plan = StudentPlanInDB(**plan_data)
        result = await self.student_plans_collection.insert_one(plan.model_dump(by_alias=True, exclude={"id"}))
        plan.id = result.inserted_id
        logger.info(f"Created plan for student {plan.student_id} in degree {plan.degree_id}")
        return plan

    async def get_student_plan(self, student_id: str, degree_id: str) -> Optional[StudentPlanInDB]:
        """Get student's active plan for a specific degree."""
        plan_doc = await self.student_plans_collection.find_one({
            "student_id": student_id,
            "degree_id": degree_id,
            "is_active": True
        })
        if not plan_doc:
            return None
        return StudentPlanInDB(**plan_doc)

    async def get_or_create_student_plan(self, student_id: str, degree_id: str, user_id: str) -> StudentPlanInDB:
        """Get student plan or create if it doesn't exist."""
        plan = await self.get_student_plan(student_id, degree_id)
        if not plan:
            plan = await self.create_student_plan({
                "student_id": student_id,
                "degree_id": degree_id,
                "user_id": user_id,
                "plan_name": "Default Plan",
                "is_active": True
            })
        return plan

    async def update_student_plan(
        self,
        student_id: str,
        degree_id: str,
        plan_data: Dict[str, Any]
    ) -> Optional[StudentPlanInDB]:
        """Update student's career plan."""
        # Convert plan_data to semester plans if needed
        if "semester_plans" in plan_data and isinstance(plan_data["semester_plans"], list):
            semester_plans = []
            for sp_data in plan_data["semester_plans"]:
                # Convert planned subjects
                planned_subjects = []
                for ps_data in sp_data.get("planned_subjects", []):
                    planned_subjects.append(PlannedSubject(**ps_data).model_dump())

                semester_plans.append(SemesterPlan(
                    semester=sp_data["semester"],
                    planned_subjects=planned_subjects,
                    total_credits=sp_data.get("total_credits", 0),
                    notes=sp_data.get("notes")
                ).model_dump())

            plan_data["semester_plans"] = semester_plans

        plan_data["updated_at"] = datetime.utcnow()

        result = await self.student_plans_collection.update_one(
            {
                "student_id": student_id,
                "degree_id": degree_id,
                "is_active": True
            },
            {"$set": plan_data}
        )

        if result.matched_count == 0:
            return None

        return await self.get_student_plan(student_id, degree_id)

    async def add_semester_to_plan(
        self,
        student_id: str,
        degree_id: str,
        semester_data: Dict[str, Any]
    ) -> Optional[StudentPlanInDB]:
        """Add a semester to student's plan."""
        # Convert to SemesterPlan model
        planned_subjects = []
        for ps_data in semester_data.get("planned_subjects", []):
            planned_subjects.append(PlannedSubject(**ps_data).model_dump())

        semester_plan = SemesterPlan(
            semester=semester_data["semester"],
            planned_subjects=planned_subjects,
            total_credits=semester_data.get("total_credits", 0),
            notes=semester_data.get("notes")
        )

        result = await self.student_plans_collection.update_one(
            {
                "student_id": student_id,
                "degree_id": degree_id,
                "is_active": True
            },
            {
                "$push": {"semester_plans": semester_plan.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.matched_count == 0:
            return None

        return await self.get_student_plan(student_id, degree_id)

    async def delete_student_plan(self, student_id: str, degree_id: str) -> bool:
        """Delete student's plan."""
        result = await self.student_plans_collection.delete_one({
            "student_id": student_id,
            "degree_id": degree_id,
            "is_active": True
        })
        return result.deleted_count > 0


# Global instance (initialized at startup)
academic_service: Optional[AcademicService] = None


def get_academic_service() -> AcademicService:
    """Get the global academic service instance."""
    if academic_service is None:
        raise RuntimeError("Academic service not initialized")
    return academic_service


def init_academic_service(db: AsyncIOMotorDatabase) -> None:
    """Initialize the global academic service instance."""
    global academic_service
    academic_service = AcademicService(db)
    logger.info("Academic service initialized")

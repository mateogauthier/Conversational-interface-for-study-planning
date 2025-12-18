"""Pydantic models for MongoDB documents."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId to work with Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserStatistics(BaseModel):
    """User statistics embedded model."""

    total_uploads: int = 0
    total_queries: int = 0
    total_storage_bytes: int = 0
    last_activity: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class UserInDB(BaseModel):
    """User document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    auth0_id: str = Field(..., description="Auth0 user ID (sub claim)")
    email: str
    name: Optional[str] = None
    role: str = Field(..., description="User role: admin or student")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    statistics: UserStatistics = Field(default_factory=UserStatistics)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Flexible field for future extensions")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class FileFeedbackStats(BaseModel):
    """File feedback statistics embedded model."""

    total_uses: int = Field(default=0, description="Total times file was used in conversations")
    total_views: int = Field(default=0, description="Total times file was viewed (opened/listed)")
    total_likes: int = Field(default=0, description="Total likes received")
    total_dislikes: int = Field(default=0, description="Total dislikes received")
    last_used: Optional[datetime] = Field(None, description="Last time file was used")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class FileMetadataInDB(BaseModel):
    """File metadata document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    filename: str
    user_id: str = Field(..., description="MongoDB user ID (ObjectId as string)")
    auth0_id: str = Field(..., description="Auth0 user ID for quick lookups")
    is_public: bool = Field(..., description="True if file is public (admin), False if private (student)")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension")
    gridfs_file_id: Optional[str] = Field(None, description="GridFS file ID (ObjectId as string)")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = Field(default=False, description="Whether file has been processed by RAG")
    chunk_count: int = Field(default=0, description="Number of chunks generated")
    feedback_stats: FileFeedbackStats = Field(default_factory=FileFeedbackStats, description="Feedback statistics for this file")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class ConversationInDB(BaseModel):
    """Conversation document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="MongoDB user ID (ObjectId as string)")
    auth0_id: str = Field(..., description="Auth0 user ID for quick lookups")
    title: str = Field(..., description="Auto-generated from first message")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = Field(default=0, description="Total number of messages in conversation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata (model, language, etc.)")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class MessageInDB(BaseModel):
    """Message document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    conversation_id: str = Field(..., description="Conversation ID (ObjectId as string)")
    role: Literal["user", "assistant"] = Field(..., description="Message sender role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_used: Optional[str] = Field(None, description="LLM model used for assistant messages")
    source_files: List[str] = Field(default_factory=list, description="List of source file names used for this response")
    feedback: Optional[Literal["like", "dislike"]] = Field(None, description="User feedback for this message (assistant only)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata (sources, token count, etc.)")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class FeedbackInDB(BaseModel):
    """Feedback document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="MongoDB user ID (ObjectId as string)")
    auth0_id: str = Field(..., description="Auth0 user ID for quick lookups")
    user_email: Optional[str] = Field(None, description="User email for display")
    message_id: Optional[str] = Field(None, description="Message ID if feedback is tied to a specific message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID if feedback is tied to a conversation")
    rating: Optional[Literal["like", "dislike"]] = Field(None, description="Rating (like/dislike)")
    comment: str = Field(..., description="Written feedback text")
    files_referenced: List[str] = Field(default_factory=list, description="Files that were referenced in the context")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata (sentiment, category, etc.)")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


# ============================================
# Academic System Models
# ============================================

class SubjectInDB(BaseModel):
    """Subject details embedded in degree or as standalone."""

    subject_id: str = Field(..., description="Unique subject code (e.g., MAT101)")
    name: str = Field(..., description="Subject name")
    credits: int = Field(..., description="Credit hours")
    department: Optional[str] = Field(None, description="Department offering the subject")
    description: Optional[str] = Field(None, description="Subject description")
    prerequisites: List[str] = Field(default_factory=list, description="List of prerequisite subject_ids")
    semester_offered: Optional[int] = Field(None, description="Suggested semester in curriculum (1-based)")

    model_config = ConfigDict(
        populate_by_name=True
    )


class DegreeInDB(BaseModel):
    """Degree/Curriculum document model for MongoDB.

    Represents: UNIVERSITY#, DEGREE#degree_id -> Currícula general de la carrera
    """

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    degree_id: str = Field(..., description="Unique degree code (e.g., CS-ENG-2024)")
    degree_name: str = Field(..., description="Degree name (e.g., Computer Engineering)")
    university: str = Field(default="UNIVERSITY", description="University identifier")
    total_credits: int = Field(..., description="Total credits required for graduation")
    duration_semesters: int = Field(..., description="Expected duration in semesters")
    description: Optional[str] = Field(None, description="Degree description")
    department: Optional[str] = Field(None, description="Department managing the degree")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional degree metadata")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class DegreeSubjectInDB(BaseModel):
    """Subject in a degree curriculum with detailed information.

    Represents: DEGREE#degree_id, SUBJECTS#subject_id -> Información detallada de una asignatura
    """

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    degree_id: str = Field(..., description="Degree this subject belongs to")
    subject_id: str = Field(..., description="Subject code")
    name: str = Field(..., description="Subject name")
    credits: int = Field(..., description="Credit hours")
    department: Optional[str] = Field(None, description="Department")
    description: Optional[str] = Field(None, description="Subject description")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite subject_ids")
    corequisites: List[str] = Field(default_factory=list, description="Corequisite subject_ids")
    semester_offered: int = Field(..., description="Suggested semester (1-based)")
    is_elective: bool = Field(default=False, description="Whether subject is elective")
    syllabus_url: Optional[str] = Field(None, description="Link to syllabus")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional subject metadata")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class StudentSubjectRecord(BaseModel):
    """Embedded model for a single subject record in student's transcript."""

    subject_id: str = Field(..., description="Subject code")
    subject_name: str = Field(..., description="Subject name")
    credits: int = Field(..., description="Credit hours")
    grade: Optional[float] = Field(None, description="Numeric grade (0-100)")
    letter_grade: Optional[str] = Field(None, description="Letter grade (A, B, C, etc.)")
    status: str = Field(..., description="Status: Passed, Failed, In Progress, Dropped, etc.")
    semester: str = Field(..., description="Semester taken (e.g., 2023-1)")
    attempt_number: int = Field(default=1, description="Attempt number (for retakes)")
    completion_date: Optional[datetime] = Field(None, description="Date completed")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class StudentSchoolingInDB(BaseModel):
    """Student's academic transcript/history for a specific degree.

    Represents: DEGREE#degree_id, STUDENT#student_id -> Escolaridad (historial) del estudiante
    """

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    degree_id: str = Field(..., description="Degree student is enrolled in")
    student_id: str = Field(..., description="Student identifier (auth0_id)")
    user_id: str = Field(..., description="MongoDB user ID reference")
    enrollment_date: datetime = Field(default_factory=datetime.utcnow, description="Date enrolled in degree")
    expected_graduation: Optional[datetime] = Field(None, description="Expected graduation date")
    current_semester: Optional[str] = Field(None, description="Current semester (e.g., 2024-1)")
    academic_status: str = Field(default="Active", description="Active, Suspended, Graduated, etc.")

    # Academic records
    completed_subjects: List[StudentSubjectRecord] = Field(default_factory=list, description="Completed subjects")
    in_progress_subjects: List[StudentSubjectRecord] = Field(default_factory=list, description="Current subjects")

    # Statistics
    total_credits_earned: int = Field(default=0, description="Total credits completed")
    total_credits_attempted: int = Field(default=0, description="Total credits attempted")
    gpa: float = Field(default=0.0, description="Grade point average")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional transcript metadata")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class PlannedSubject(BaseModel):
    """Embedded model for a planned subject in future semester."""

    subject_id: str = Field(..., description="Subject code")
    subject_name: str = Field(..., description="Subject name")
    credits: int = Field(..., description="Credit hours")
    priority: Optional[str] = Field(None, description="High, Medium, Low")
    notes: Optional[str] = Field(None, description="Planning notes")

    model_config = ConfigDict(
        populate_by_name=True
    )


class SemesterPlan(BaseModel):
    """Embedded model for a single semester's plan."""

    semester: str = Field(..., description="Semester identifier (e.g., 2024-1)")
    planned_subjects: List[PlannedSubject] = Field(default_factory=list, description="Subjects planned for this semester")
    total_credits: int = Field(default=0, description="Total credits planned")
    notes: Optional[str] = Field(None, description="Semester notes")

    model_config = ConfigDict(
        populate_by_name=True
    )


class StudentPlanInDB(BaseModel):
    """Student's future career/study plan.

    Represents: DEGREE#degree_id, STUDENT-PLAN#student_id -> Plan de carrera futuro del estudiante
    """

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    degree_id: str = Field(..., description="Degree student is planning for")
    student_id: str = Field(..., description="Student identifier (auth0_id)")
    user_id: str = Field(..., description="MongoDB user ID reference")
    plan_name: Optional[str] = Field(None, description="Optional plan name")

    # Future semester plans
    semester_plans: List[SemesterPlan] = Field(default_factory=list, description="Planned semesters")

    # Planning metadata
    target_graduation: Optional[datetime] = Field(None, description="Target graduation date")
    is_active: bool = Field(default=True, description="Whether this is the active plan")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional plan metadata")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )

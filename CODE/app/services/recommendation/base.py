"""Abstract base class for recommendation algorithms."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class CourseRecommendation:
    """A single course recommendation with confidence score."""
    subject_id: str
    subject_name: str
    p_pass: float        # Probability of passing (0.0 – 1.0)
    final_score: float   # Composite score blending p_pass with academic relevance
    rank: int
    is_core: bool        # True if this is a core (non-elective) course
    reason: str          # Human-readable explanation


class BaseRecommender(ABC):
    """Interface that all recommendation algorithms must implement.

    Subclasses handle their own training data extraction, feature
    engineering, model fitting, and inference.  The RecommendationService
    orchestrates lifecycle (train → recommend) without knowing internals.
    """

    @abstractmethod
    async def train(self, db) -> None:
        """Train the model using data from MongoDB.

        Args:
            db: AsyncIOMotorDatabase instance.
        """

    @abstractmethod
    async def recommend(
        self,
        student_id: str,
        degree_id: str,
        db,
        n_recommendations: int = 10,
    ) -> List[CourseRecommendation]:
        """Return ranked course recommendations for a student.

        Args:
            student_id: Auth0 ID of the student.
            degree_id: Degree programme identifier.
            db: AsyncIOMotorDatabase instance.
            n_recommendations: Max items to return.
        """

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """True when the model is ready for inference."""

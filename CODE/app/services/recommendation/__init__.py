"""Recommendation service for course suggestions using ML algorithms."""

import logging
from typing import Dict, List, Optional

from app.services.recommendation.base import BaseRecommender, CourseRecommendation

logger = logging.getLogger(__name__)


class RecommendationService:
    """Registry and dispatcher for recommendation algorithms.

    Holds trained recommender instances and delegates recommendation
    requests to the appropriate algorithm.
    """

    def __init__(self):
        self._recommenders: Dict[str, BaseRecommender] = {}

    def register(self, name: str, recommender: BaseRecommender):
        self._recommenders[name] = recommender
        logger.info(f"Registered recommender: {name}")

    async def train_all(self, db) -> Dict[str, bool]:
        """Train all registered recommenders. Returns {name: success}."""
        results = {}
        for name, rec in self._recommenders.items():
            try:
                await rec.train(db)
                results[name] = True
                logger.info(f"Recommender '{name}' trained successfully")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to train recommender '{name}': {e}", exc_info=True)
        return results

    async def recommend(
        self,
        student_id: str,
        degree_id: str,
        db,
        algorithm: str = "random_forest",
        n_recommendations: int = 10,
    ) -> List[CourseRecommendation]:
        rec = self._recommenders.get(algorithm)
        if not rec:
            available = list(self._recommenders.keys())
            raise ValueError(f"Unknown algorithm '{algorithm}'. Available: {available}")
        if not rec.is_trained:
            raise RuntimeError(f"Recommender '{algorithm}' is not trained yet")
        return await rec.recommend(student_id, degree_id, db, n_recommendations)

    async def recommend_all(
        self,
        student_id: str,
        degree_id: str,
        db,
        n_recommendations: int = 10,
    ) -> Dict[str, List[CourseRecommendation]]:
        """Run all trained algorithms and return results keyed by algorithm name."""
        results = {}
        for name, rec in self._recommenders.items():
            if not rec.is_trained:
                logger.warning(f"Skipping untrained recommender '{name}'")
                continue
            try:
                recs = await rec.recommend(student_id, degree_id, db, n_recommendations)
                results[name] = recs
                logger.info(f"Algorithm '{name}' returned {len(recs)} recommendations")
            except Exception as e:
                logger.error(f"Algorithm '{name}' failed: {e}", exc_info=True)
        return results

    @property
    def available_algorithms(self) -> List[str]:
        return [name for name, rec in self._recommenders.items() if rec.is_trained]


# Module-level singleton
_recommendation_service: Optional[RecommendationService] = None


def get_recommendation_service() -> RecommendationService:
    if _recommendation_service is None:
        raise RuntimeError("RecommendationService not initialized")
    return _recommendation_service


def init_recommendation_service() -> RecommendationService:
    global _recommendation_service
    _recommendation_service = RecommendationService()
    return _recommendation_service

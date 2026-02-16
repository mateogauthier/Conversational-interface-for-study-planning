"""Random Forest course recommender.

Predicts the probability of a student passing each candidate course
based on features engineered from the full student population, then
blends that probability with an academic relevance score to produce
a final ranking that balances likelihood of success with curriculum
importance.

Features per (student, candidate_subject) pair:
  - subject_id          (categorical -> one-hot)
  - category            (categorical -> one-hot)
  - attempt_number      (numeric)
  - degree_year         (numeric)
  - spr                 (Subject Pass Rate - global)
  - requirements_ratio  (fraction of prerequisites already passed)
  - ssr                 (Student Success Rate - cumulative)
  - ssrc               (Student Success Rate by Category)

Relevance scoring factors:
  - core_bonus          (core courses weighted higher than electives)
  - semester_alignment  (courses closer to the student's next semester score higher)
  - unlock_value        (courses that are prerequisites for many others score higher)
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.utils import resample

from app.services.recommendation.base import BaseRecommender, CourseRecommendation
from app.services.recommendation.subject_categories import get_category

logger = logging.getLogger(__name__)

CATEGORICAL_COLS = ["subject_id", "category"]
NUMERIC_COLS = ["attempt_number", "degree_year", "spr", "requirements_ratio", "ssr", "ssrc"]

# Weights for composite final_score
WEIGHT_P_PASS = 0.4
WEIGHT_RELEVANCE = 0.6

# Weights within the relevance score
RELEVANCE_CORE_WEIGHT = 0.35
RELEVANCE_SEMESTER_WEIGHT = 0.35
RELEVANCE_UNLOCK_WEIGHT = 0.30


class RandomForestRecommender(BaseRecommender):

    def __init__(self, n_estimators: int = 400, random_state: int = 42):
        self._pipeline: Optional[Pipeline] = None
        self._subject_pass_rates: Dict[str, float] = {}
        self._subject_names: Dict[str, str] = {}
        self._subject_prerequisites: Dict[str, List[str]] = {}
        self._subject_is_elective: Dict[str, bool] = {}
        self._subject_semester: Dict[str, int] = {}
        self._unlock_counts: Dict[str, int] = {}
        self._max_unlock_count: int = 1
        self._n_estimators = n_estimators
        self._random_state = random_state

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    async def train(self, db) -> None:
        """Train on all student_schooling records in the database."""
        logger.info("RF Recommender: fetching training data ...")

        # Fetch all student records
        cursor = db.student_schooling.find({})
        students = await cursor.to_list(length=None)
        logger.info(f"RF Recommender: loaded {len(students)} student records")

        if len(students) < 10:
            raise RuntimeError("Not enough student data to train (need >= 10)")

        # Fetch subject catalogue for prerequisites, names, and metadata
        subject_cursor = db.degree_subjects.find({})
        subjects_docs = await subject_cursor.to_list(length=None)
        for s in subjects_docs:
            sid = s["subject_id"]
            self._subject_names[sid] = s.get("name", sid)
            self._subject_prerequisites[sid] = s.get("prerequisites", [])
            self._subject_is_elective[sid] = s.get("is_elective", True)
            self._subject_semester[sid] = s.get("semester_offered", 0)

        # Compute unlock counts (how many courses each subject is a prerequisite for)
        self._unlock_counts = self._compute_unlock_counts()
        self._max_unlock_count = max(self._unlock_counts.values()) if self._unlock_counts else 1

        # Compute global Subject Pass Rates
        self._subject_pass_rates = self._compute_subject_pass_rates(students)

        # Build training dataframe
        rows = self._build_training_rows(students)
        if not rows:
            raise RuntimeError("No training rows could be built")

        df = pd.DataFrame(rows)
        logger.info(f"RF Recommender: {len(df)} training rows, pass rate = {df['label'].mean():.2%}")

        X = df[CATEGORICAL_COLS + NUMERIC_COLS]
        y = df["label"]

        # Handle class imbalance via upsampling the minority class
        X, y = self._balance_classes(X, y)

        # Build sklearn pipeline
        preprocessor = ColumnTransformer(
            transformers=[
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_COLS),
                ("num", RobustScaler(), NUMERIC_COLS),
            ]
        )

        self._pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(
                n_estimators=self._n_estimators,
                random_state=self._random_state,
                n_jobs=-1,
            )),
        ])

        self._pipeline.fit(X, y)
        logger.info("RF Recommender: training complete")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    async def recommend(
        self,
        student_id: str,
        degree_id: str,
        db,
        n_recommendations: int = 10,
    ) -> List[CourseRecommendation]:
        schooling_doc = await db.student_schooling.find_one({
            "student_id": student_id,
            "degree_id": degree_id,
        })
        if not schooling_doc:
            return []

        completed = schooling_doc.get("completed_subjects", [])
        in_progress = schooling_doc.get("in_progress_subjects", [])

        completed_ids = {s["subject_id"] for s in completed}
        in_progress_ids = {s["subject_id"] for s in in_progress}
        taken_ids = completed_ids | in_progress_ids

        # Determine candidate subjects (not taken, prerequisites met)
        candidates = self._get_eligible_candidates(taken_ids, completed_ids)
        if not candidates:
            return []

        # Student-level features
        ssr = self._compute_ssr(completed)
        ssrc_map = self._compute_ssrc(completed)
        degree_year = self._compute_degree_year(schooling_doc)
        next_semester = self._estimate_next_semester(completed_ids)

        # Build inference dataframe
        rows = []
        for sid in candidates:
            category = get_category(sid)
            prereqs = self._subject_prerequisites.get(sid, [])
            met = sum(1 for p in prereqs if p in completed_ids) if prereqs else 0
            req_ratio = met / len(prereqs) if prereqs else 1.0

            rows.append({
                "subject_id": sid,
                "category": category,
                "attempt_number": 1,
                "degree_year": degree_year,
                "spr": self._subject_pass_rates.get(sid, 0.5),
                "requirements_ratio": req_ratio,
                "ssr": ssr,
                "ssrc": ssrc_map.get(category, ssr),
            })

        df = pd.DataFrame(rows)
        probas = self._pipeline.predict_proba(df[CATEGORICAL_COLS + NUMERIC_COLS])

        # Index of the positive class (1 = pass)
        pass_idx = list(self._pipeline.classes_).index(1)

        # Compute composite scores (p_pass + relevance)
        scored = []
        for i, sid in enumerate(candidates):
            p_pass = float(probas[i][pass_idx])
            relevance = self._compute_relevance_score(sid, next_semester)
            final_score = WEIGHT_P_PASS * p_pass + WEIGHT_RELEVANCE * relevance
            scored.append((sid, p_pass, relevance, final_score))

        scored.sort(key=lambda x: x[3], reverse=True)
        scored = scored[:n_recommendations]

        recommendations = []
        for rank, (sid, p_pass, relevance, final_score) in enumerate(scored, start=1):
            name = self._subject_names.get(sid, sid)
            is_core = not self._subject_is_elective.get(sid, True)
            recommendations.append(CourseRecommendation(
                subject_id=sid,
                subject_name=name,
                p_pass=round(p_pass, 3),
                final_score=round(final_score, 3),
                rank=rank,
                is_core=is_core,
                reason=self._build_reason(p_pass, final_score, is_core, sid),
            ))

        return recommendations

    @property
    def is_trained(self) -> bool:
        return self._pipeline is not None

    # ------------------------------------------------------------------
    # Relevance scoring
    # ------------------------------------------------------------------

    def _compute_unlock_counts(self) -> Dict[str, int]:
        """For each subject, count how many other subjects list it as a prerequisite."""
        counts: Dict[str, int] = defaultdict(int)
        for prereqs in self._subject_prerequisites.values():
            for p in prereqs:
                counts[p] += 1
        return dict(counts)

    def _compute_relevance_score(self, subject_id: str, next_semester: int) -> float:
        """Compute academic relevance score (0.0 - 1.0) for a candidate subject.

        Combines three factors:
        - Core course bonus: core subjects are more important than electives
        - Semester alignment: courses matching the student's progression score higher
        - Unlock value: courses that are prerequisites for many others score higher
        """
        # Factor 1: Core vs elective
        is_elective = self._subject_is_elective.get(subject_id, True)
        core_score = 0.0 if is_elective else 1.0

        # Factor 2: Semester alignment
        sem = self._subject_semester.get(subject_id, 0)
        if sem == 0:
            # Elective (no fixed semester) - low alignment score
            semester_score = 0.2
        else:
            # Closer to next_semester = higher score, with decay
            distance = abs(sem - next_semester)
            semester_score = max(0.0, 1.0 - distance * 0.25)

        # Factor 3: Unlock value (normalized)
        unlock = self._unlock_counts.get(subject_id, 0)
        unlock_score = unlock / self._max_unlock_count if self._max_unlock_count > 0 else 0.0

        return (
            RELEVANCE_CORE_WEIGHT * core_score
            + RELEVANCE_SEMESTER_WEIGHT * semester_score
            + RELEVANCE_UNLOCK_WEIGHT * unlock_score
        )

    def _estimate_next_semester(self, completed_ids: Set[str]) -> int:
        """Estimate the student's next logical semester based on completed core courses."""
        max_completed_sem = 0
        for sid in completed_ids:
            sem = self._subject_semester.get(sid, 0)
            if sem > 0:
                max_completed_sem = max(max_completed_sem, sem)
        return max_completed_sem + 1

    # ------------------------------------------------------------------
    # Feature helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_subject_pass_rates(students: list) -> Dict[str, float]:
        """Global pass rate per subject across the whole population."""
        totals: Dict[str, int] = defaultdict(int)
        passes: Dict[str, int] = defaultdict(int)
        for st in students:
            for sub in st.get("completed_subjects", []):
                sid = sub["subject_id"]
                totals[sid] += 1
                if sub.get("status") == "Passed":
                    passes[sid] += 1
        return {
            sid: passes[sid] / totals[sid] if totals[sid] > 0 else 0.5
            for sid in totals
        }

    def _build_training_rows(self, students: list) -> list:
        """Build one row per (student, subject-attempt) for the training set.

        Features are computed cumulatively: for each subject-attempt,
        SSR and SSRC reflect only earlier attempts by that student.
        """
        rows = []
        for st in students:
            completed = st.get("completed_subjects", [])
            if not completed:
                continue

            # Sort chronologically by semester then by subject_id for stability
            sorted_subs = sorted(completed, key=lambda s: (s.get("semester", ""), s["subject_id"]))

            completed_so_far: Set[str] = set()
            total_so_far = 0
            passed_so_far = 0
            cat_total: Dict[str, int] = defaultdict(int)
            cat_passed: Dict[str, int] = defaultdict(int)

            degree_year = self._compute_degree_year(st)

            for sub in sorted_subs:
                sid = sub["subject_id"]
                status = sub.get("status", "")
                category = get_category(sid)
                is_pass = 1 if status == "Passed" else 0

                # Compute features BEFORE counting this attempt
                ssr = passed_so_far / total_so_far if total_so_far > 0 else 0.5
                ssrc = cat_passed[category] / cat_total[category] if cat_total[category] > 0 else 0.5

                prereqs = self._subject_prerequisites.get(sid, [])
                met = sum(1 for p in prereqs if p in completed_so_far) if prereqs else 0
                req_ratio = met / len(prereqs) if prereqs else 1.0

                rows.append({
                    "subject_id": sid,
                    "category": category,
                    "attempt_number": sub.get("attempt_number", 1),
                    "degree_year": degree_year,
                    "spr": self._subject_pass_rates.get(sid, 0.5),
                    "requirements_ratio": req_ratio,
                    "ssr": ssr,
                    "ssrc": ssrc,
                    "label": is_pass,
                })

                # Update running counters
                total_so_far += 1
                passed_so_far += is_pass
                cat_total[category] += 1
                cat_passed[category] += is_pass
                if is_pass:
                    completed_so_far.add(sid)

        return rows

    @staticmethod
    def _balance_classes(X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """Upsample the minority class to match the majority."""
        combined = pd.concat([X, y.rename("label")], axis=1)
        majority = combined[combined["label"] == combined["label"].mode()[0]]
        minority = combined[combined["label"] != combined["label"].mode()[0]]

        if len(minority) == 0 or len(majority) == 0:
            return X, y

        minority_upsampled = resample(
            minority,
            replace=True,
            n_samples=len(majority),
            random_state=42,
        )
        balanced = pd.concat([majority, minority_upsampled])
        return balanced.drop("label", axis=1), balanced["label"]

    @staticmethod
    def _compute_ssr(completed: list) -> float:
        """Student Success Rate from completed subjects."""
        if not completed:
            return 0.5
        passed = sum(1 for s in completed if s.get("status") == "Passed")
        return passed / len(completed)

    @staticmethod
    def _compute_ssrc(completed: list) -> Dict[str, float]:
        """Student Success Rate by Category."""
        cat_total: Dict[str, int] = defaultdict(int)
        cat_passed: Dict[str, int] = defaultdict(int)
        for s in completed:
            cat = get_category(s["subject_id"])
            cat_total[cat] += 1
            if s.get("status") == "Passed":
                cat_passed[cat] += 1
        return {
            cat: cat_passed[cat] / cat_total[cat] if cat_total[cat] > 0 else 0.5
            for cat in cat_total
        }

    @staticmethod
    def _compute_degree_year(student_doc: dict) -> int:
        """Estimate the student's current academic year (1-based)."""
        enrollment = student_doc.get("enrollment_date", "")
        current = student_doc.get("current_semester", "")
        if not enrollment or not current:
            return 1
        try:
            # enrollment_date is ISO format, current_semester is "YYYY-S"
            enroll_year = int(str(enrollment)[:4])
            current_year = int(current.split("-")[0])
            return max(1, current_year - enroll_year + 1)
        except (ValueError, IndexError):
            return 1

    def _get_eligible_candidates(
        self,
        taken_ids: Set[str],
        completed_ids: Set[str],
    ) -> List[str]:
        """Subjects not yet taken whose prerequisites are all met."""
        candidates = []
        for sid, prereqs in self._subject_prerequisites.items():
            if sid in taken_ids:
                continue
            if all(p in completed_ids for p in prereqs):
                candidates.append(sid)
        return candidates

    @staticmethod
    def _build_reason(
        p_pass: float,
        final_score: float,
        is_core: bool,
        subject_id: str,
    ) -> str:
        parts = []

        if is_core:
            parts.append("Core curriculum course.")
        else:
            parts.append("Elective course.")

        if p_pass >= 0.8:
            parts.append(f"High predicted success ({p_pass:.0%}).")
        elif p_pass >= 0.6:
            parts.append(f"Moderate predicted success ({p_pass:.0%}).")
        else:
            parts.append(f"Lower predicted success ({p_pass:.0%}).")

        parts.append(f"Overall recommendation score: {final_score:.0%}.")

        return " ".join(parts)

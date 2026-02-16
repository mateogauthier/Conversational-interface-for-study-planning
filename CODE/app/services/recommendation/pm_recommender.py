"""Pattern Mining (PM) course recommender.

Finds successful students with similar course-taking patterns and
recommends what those peers took next. Uses pairwise course relationship
"footprints" to measure trajectory similarity.

Training:
  1. Builds a footprint for each student: pairwise relationships between
     courses (same-term, direct succession, skip succession)
  2. Identifies successful students (high pass rate)
  3. Stores successful profiles with footprints and course statistics

Inference:
  1. Builds the target student's footprint
  2. Compares against successful student footprints
  3. From similar peers, collects their next courses
  4. Ranks by peer support and course performance
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from app.services.recommendation.base import BaseRecommender, CourseRecommendation

logger = logging.getLogger(__name__)

# Peer matching parameters
DEFAULT_MIN_SIMILARITY = 0.3
DEFAULT_MIN_PASS_RATE = 0.7

# Weights for composite final_score
WEIGHT_PEER = 0.5
WEIGHT_RELEVANCE = 0.5

# Weights within the relevance score
RELEVANCE_CORE_WEIGHT = 0.35
RELEVANCE_SEMESTER_WEIGHT = 0.35
RELEVANCE_UNLOCK_WEIGHT = 0.30

# Relationship types for footprint
REL_SAME_TERM = "||"
REL_NEXT_TERM = "->"
REL_SKIP_TERM = "->>"


class PatternMiningRecommender(BaseRecommender):

    def __init__(
        self,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
        min_pass_rate: float = DEFAULT_MIN_PASS_RATE,
    ):
        self._min_similarity = min_similarity
        self._min_pass_rate = min_pass_rate
        self._successful_profiles: List[Dict] = []
        self._course_stats: Dict[str, Dict] = {}
        self._subject_names: Dict[str, str] = {}
        self._subject_prerequisites: Dict[str, List[str]] = {}
        self._subject_is_elective: Dict[str, bool] = {}
        self._subject_semester: Dict[str, int] = {}
        self._unlock_counts: Dict[str, int] = {}
        self._max_unlock_count: int = 1
        self._trained = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    async def train(self, db) -> None:
        """Train on all student_schooling records in the database."""
        logger.info("PM Recommender: fetching training data ...")

        cursor = db.student_schooling.find({})
        students = await cursor.to_list(length=None)
        logger.info(f"PM Recommender: loaded {len(students)} student records")

        if len(students) < 10:
            raise RuntimeError("Not enough student data to train PM (need >= 10)")

        # Fetch subject catalogue
        subject_cursor = db.degree_subjects.find({})
        subjects_docs = await subject_cursor.to_list(length=None)
        for s in subjects_docs:
            sid = s["subject_id"]
            self._subject_names[sid] = s.get("name", sid)
            self._subject_prerequisites[sid] = s.get("prerequisites", [])
            self._subject_is_elective[sid] = s.get("is_elective", True)
            self._subject_semester[sid] = s.get("semester_offered", 0)

        self._unlock_counts = self._compute_unlock_counts()
        self._max_unlock_count = max(self._unlock_counts.values()) if self._unlock_counts else 1

        # Compute per-course statistics
        self._course_stats = self._compute_course_stats(students)

        # Build profiles for successful students
        self._successful_profiles = self._build_successful_profiles(students)
        logger.info(
            f"PM Recommender: {len(self._successful_profiles)} successful student profiles "
            f"(out of {len(students)} total)"
        )

        self._trained = True
        logger.info("PM Recommender: training complete")

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

        # Build student's term-grouped courses and footprint
        student_terms = self._group_by_term(completed, passed_only=True)
        if not student_terms:
            return []

        student_footprint = self._build_footprint(student_terms)
        student_course_set = {sid for term in student_terms for sid in term}

        # Get eligible candidates
        eligible = set(self._get_eligible_candidates(taken_ids, completed_ids))
        if not eligible:
            return []

        next_semester = self._estimate_next_semester(completed_ids)
        student_next_term_idx = len(student_terms)

        # Find similar successful peers and collect their next courses
        candidate_support: Dict[str, float] = defaultdict(float)
        candidate_peer_count: Dict[str, int] = defaultdict(int)

        for profile in self._successful_profiles:
            sim = self._compute_similarity(student_footprint, profile["footprint"])
            if sim < self._min_similarity:
                continue

            # Get courses this peer took in the term after the student's current point
            peer_terms = profile["terms"]
            if student_next_term_idx < len(peer_terms):
                for sid in peer_terms[student_next_term_idx]:
                    if sid in eligible and sid not in student_course_set:
                        candidate_support[sid] += sim
                        candidate_peer_count[sid] += 1

            # Also consider courses from subsequent terms
            for t_idx in range(student_next_term_idx + 1, min(len(peer_terms), student_next_term_idx + 3)):
                for sid in peer_terms[t_idx]:
                    if sid in eligible and sid not in student_course_set:
                        # Decay for later terms
                        decay = 0.5 ** (t_idx - student_next_term_idx)
                        candidate_support[sid] += sim * decay
                        candidate_peer_count[sid] += 1

        # Score all eligible candidates
        scored = []
        for sid in eligible:
            peer_score = candidate_support.get(sid, 0.0)

            # Normalize peer score
            max_peer = max(candidate_support.values()) if candidate_support else 1.0
            norm_peer = peer_score / max_peer if max_peer > 0 else 0.0

            # Boost by course performance
            stats = self._course_stats.get(sid, {})
            p_pass = stats.get("pass_rate", 0.5)
            avg_grade = stats.get("avg_grade", 0.0)
            grade_boost = 1.0 + (avg_grade / 12.0) if avg_grade > 0 else 1.0
            norm_peer *= grade_boost

            # Clip to 0-1
            norm_peer = min(1.0, norm_peer)

            relevance = self._compute_relevance_score(sid, next_semester)
            final_score = WEIGHT_PEER * norm_peer + WEIGHT_RELEVANCE * relevance

            scored.append((sid, p_pass, final_score, candidate_peer_count.get(sid, 0)))

        scored.sort(key=lambda x: x[2], reverse=True)
        scored = scored[:n_recommendations]

        recommendations = []
        for rank, (sid, p_pass, final_score, peer_count) in enumerate(scored, start=1):
            name = self._subject_names.get(sid, sid)
            is_core = not self._subject_is_elective.get(sid, True)
            recommendations.append(CourseRecommendation(
                subject_id=sid,
                subject_name=name,
                p_pass=round(p_pass, 3),
                final_score=round(final_score, 3),
                rank=rank,
                is_core=is_core,
                reason=self._build_reason(p_pass, final_score, is_core, peer_count),
            ))

        return recommendations

    @property
    def is_trained(self) -> bool:
        return self._trained

    # ------------------------------------------------------------------
    # Footprint building
    # ------------------------------------------------------------------

    def _build_successful_profiles(self, students: list) -> List[Dict]:
        """Build profiles for students with high pass rates."""
        profiles = []
        for st in students:
            completed = st.get("completed_subjects", [])
            if len(completed) < 3:
                continue

            passed = sum(1 for s in completed if s.get("status") == "Passed")
            pass_rate = passed / len(completed)
            if pass_rate < self._min_pass_rate:
                continue

            terms = self._group_by_term(completed, passed_only=True)
            if len(terms) < 2:
                continue

            footprint = self._build_footprint(terms)
            profiles.append({
                "terms": terms,
                "footprint": footprint,
                "pass_rate": pass_rate,
            })

        return profiles

    @staticmethod
    def _group_by_term(completed: list, passed_only: bool = True) -> List[List[str]]:
        """Group completed subjects into ordered terms (semesters)."""
        term_map: Dict[str, List[str]] = defaultdict(list)
        for sub in completed:
            if passed_only and sub.get("status") != "Passed":
                continue
            semester = sub.get("semester", "")
            if not semester:
                continue
            term_map[semester].append(sub["subject_id"])

        # Sort terms chronologically and return as list of lists
        sorted_terms = sorted(term_map.keys())
        return [sorted(term_map[t]) for t in sorted_terms]

    @staticmethod
    def _build_footprint(terms: List[List[str]]) -> Dict[Tuple[str, str], str]:
        """Build pairwise course relationship footprint.

        For each pair of courses (a, b), records their temporal relationship:
        - "||" same term
        - "->" consecutive terms
        - "->>" non-consecutive terms (skip)
        """
        footprint: Dict[Tuple[str, str], str] = {}

        for t_idx, term in enumerate(terms):
            # Same-term relationships
            for i in range(len(term)):
                for j in range(i + 1, len(term)):
                    a, b = min(term[i], term[j]), max(term[i], term[j])
                    footprint[(a, b)] = REL_SAME_TERM

            # Cross-term relationships
            for future_idx in range(t_idx + 1, len(terms)):
                rel = REL_NEXT_TERM if future_idx == t_idx + 1 else REL_SKIP_TERM
                for a in term:
                    for b in terms[future_idx]:
                        key = (min(a, b), max(a, b))
                        # Don't overwrite a closer relationship
                        if key not in footprint:
                            footprint[key] = rel

        return footprint

    @staticmethod
    def _compute_similarity(
        fp_a: Dict[Tuple[str, str], str],
        fp_b: Dict[Tuple[str, str], str],
    ) -> float:
        """Compute similarity between two footprints.

        Similarity = matching_pairs / total_pairs across the shared course universe.
        """
        all_keys = set(fp_a.keys()) | set(fp_b.keys())
        if not all_keys:
            return 0.0

        matches = 0
        for key in all_keys:
            if key in fp_a and key in fp_b and fp_a[key] == fp_b[key]:
                matches += 1

        return matches / len(all_keys)

    # ------------------------------------------------------------------
    # Course statistics
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_course_stats(students: list) -> Dict[str, Dict]:
        totals: Dict[str, int] = defaultdict(int)
        passes: Dict[str, int] = defaultdict(int)
        grade_sums: Dict[str, float] = defaultdict(float)
        grade_counts: Dict[str, int] = defaultdict(int)

        for st in students:
            for sub in st.get("completed_subjects", []):
                sid = sub["subject_id"]
                totals[sid] += 1
                if sub.get("status") == "Passed":
                    passes[sid] += 1
                grade = sub.get("grade")
                if grade is not None:
                    grade_sums[sid] += float(grade)
                    grade_counts[sid] += 1

        stats = {}
        for sid in totals:
            stats[sid] = {
                "pass_rate": passes[sid] / totals[sid] if totals[sid] > 0 else 0.5,
                "avg_grade": grade_sums[sid] / grade_counts[sid] if grade_counts[sid] > 0 else 0.0,
                "count": totals[sid],
            }
        return stats

    # ------------------------------------------------------------------
    # Relevance scoring (shared logic with RF)
    # ------------------------------------------------------------------

    def _compute_unlock_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for prereqs in self._subject_prerequisites.values():
            for p in prereqs:
                counts[p] += 1
        return dict(counts)

    def _compute_relevance_score(self, subject_id: str, next_semester: int) -> float:
        is_elective = self._subject_is_elective.get(subject_id, True)
        core_score = 0.0 if is_elective else 1.0

        sem = self._subject_semester.get(subject_id, 0)
        if sem == 0:
            semester_score = 0.2
        else:
            distance = abs(sem - next_semester)
            semester_score = max(0.0, 1.0 - distance * 0.25)

        unlock = self._unlock_counts.get(subject_id, 0)
        unlock_score = unlock / self._max_unlock_count if self._max_unlock_count > 0 else 0.0

        return (
            RELEVANCE_CORE_WEIGHT * core_score
            + RELEVANCE_SEMESTER_WEIGHT * semester_score
            + RELEVANCE_UNLOCK_WEIGHT * unlock_score
        )

    def _estimate_next_semester(self, completed_ids: Set[str]) -> int:
        max_sem = 0
        for sid in completed_ids:
            sem = self._subject_semester.get(sid, 0)
            if sem > 0:
                max_sem = max(max_sem, sem)
        return max_sem + 1

    def _get_eligible_candidates(
        self,
        taken_ids: Set[str],
        completed_ids: Set[str],
    ) -> List[str]:
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
        peer_count: int,
    ) -> str:
        parts = []
        if is_core:
            parts.append("Core curriculum course.")
        else:
            parts.append("Elective course.")

        if peer_count > 0:
            parts.append(
                f"Recommended by {peer_count} similar successful student(s)."
            )
        else:
            parts.append("Recommended based on academic relevance.")

        parts.append(f"Historical pass rate: {p_pass:.0%}.")
        parts.append(f"Overall recommendation score: {final_score:.0%}.")
        return " ".join(parts)

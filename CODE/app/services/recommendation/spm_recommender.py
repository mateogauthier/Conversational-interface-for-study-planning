"""Sequential Pattern Mining (SPM) course recommender.

Discovers frequent course enrollment sequences from successful students
using a simplified PrefixSpan algorithm, then recommends the courses
that typically follow a student's current progression.

Training:
  1. Groups each student's passed courses into ordered term sequences
  2. Mines frequent subsequences with PrefixSpan (min_support threshold)
  3. Stores patterns with support and confidence metrics

Inference:
  1. Matches the student's completed sequence against discovered patterns
  2. Collects "next items" from matching patterns
  3. Scores by confidence × support, blended with academic relevance
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from app.services.recommendation.base import BaseRecommender, CourseRecommendation

logger = logging.getLogger(__name__)

# PrefixSpan parameters
DEFAULT_MIN_SUPPORT = 0.05
DEFAULT_MAX_PATTERN_LEN = 6

# Weights for composite final_score
WEIGHT_PATTERN = 0.5
WEIGHT_RELEVANCE = 0.5

# Weights within the relevance score (same as RF for consistency)
RELEVANCE_CORE_WEIGHT = 0.35
RELEVANCE_SEMESTER_WEIGHT = 0.35
RELEVANCE_UNLOCK_WEIGHT = 0.30


class SPMRecommender(BaseRecommender):

    def __init__(
        self,
        min_support: float = DEFAULT_MIN_SUPPORT,
        max_pattern_len: int = DEFAULT_MAX_PATTERN_LEN,
    ):
        self._min_support = min_support
        self._max_pattern_len = max_pattern_len
        self._patterns: List[Tuple[List[str], float]] = []  # (sequence, support)
        self._course_stats: Dict[str, Dict] = {}  # sid -> {pass_rate, avg_grade, count}
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
        logger.info("SPM Recommender: fetching training data ...")

        cursor = db.student_schooling.find({})
        students = await cursor.to_list(length=None)
        logger.info(f"SPM Recommender: loaded {len(students)} student records")

        if len(students) < 10:
            raise RuntimeError("Not enough student data to train SPM (need >= 10)")

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

        # Build ordered sequences from successful outcomes
        sequences = self._build_sequences(students)
        logger.info(f"SPM Recommender: built {len(sequences)} sequences")

        # Compute per-course statistics
        self._course_stats = self._compute_course_stats(students)

        # Run PrefixSpan
        self._patterns = self._prefixspan(sequences)
        logger.info(f"SPM Recommender: discovered {len(self._patterns)} patterns")

        self._trained = True
        logger.info("SPM Recommender: training complete")

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

        # Build student's ordered sequence of passed courses
        student_seq = self._build_student_sequence(completed)

        # Get eligible candidates (prerequisites met, not taken)
        eligible = set(self._get_eligible_candidates(taken_ids, completed_ids))
        if not eligible:
            return []

        next_semester = self._estimate_next_semester(completed_ids)

        # Match patterns and collect next-item candidates
        candidate_scores: Dict[str, float] = defaultdict(float)
        candidate_counts: Dict[str, int] = defaultdict(int)

        for pattern, support in self._patterns:
            match_len = self._longest_prefix_match(student_seq, pattern)
            if match_len == 0:
                continue

            # The items after the matched prefix are recommendations
            next_items = pattern[match_len:]
            confidence = match_len / len(pattern) if len(pattern) > 0 else 0.0

            for sid in next_items:
                if sid in eligible:
                    score = confidence * support
                    candidate_scores[sid] += score
                    candidate_counts[sid] += 1

        # Score all candidates (pattern-matched + fallback for eligible with no matches)
        scored = []
        for sid in eligible:
            pattern_score = candidate_scores.get(sid, 0.0)

            # Normalize pattern score (0-1 range)
            max_pattern = max(candidate_scores.values()) if candidate_scores else 1.0
            norm_pattern = pattern_score / max_pattern if max_pattern > 0 else 0.0

            relevance = self._compute_relevance_score(sid, next_semester)
            final_score = WEIGHT_PATTERN * norm_pattern + WEIGHT_RELEVANCE * relevance

            # Use course pass rate as p_pass proxy
            stats = self._course_stats.get(sid, {})
            p_pass = stats.get("pass_rate", 0.5)

            scored.append((sid, p_pass, final_score, candidate_counts.get(sid, 0)))

        scored.sort(key=lambda x: x[2], reverse=True)
        scored = scored[:n_recommendations]

        recommendations = []
        for rank, (sid, p_pass, final_score, pattern_count) in enumerate(scored, start=1):
            name = self._subject_names.get(sid, sid)
            is_core = not self._subject_is_elective.get(sid, True)
            recommendations.append(CourseRecommendation(
                subject_id=sid,
                subject_name=name,
                p_pass=round(p_pass, 3),
                final_score=round(final_score, 3),
                rank=rank,
                is_core=is_core,
                reason=self._build_reason(p_pass, final_score, is_core, pattern_count),
            ))

        return recommendations

    @property
    def is_trained(self) -> bool:
        return self._trained

    # ------------------------------------------------------------------
    # PrefixSpan algorithm
    # ------------------------------------------------------------------

    def _prefixspan(
        self,
        sequences: List[List[str]],
    ) -> List[Tuple[List[str], float]]:
        """Simplified PrefixSpan: mine frequent sequential patterns."""
        n_sequences = len(sequences)
        if n_sequences == 0:
            return []

        min_count = max(2, int(self._min_support * n_sequences))
        results: List[Tuple[List[str], float]] = []

        # Find frequent 1-items
        item_counts: Dict[str, int] = defaultdict(int)
        for seq in sequences:
            seen = set()
            for item in seq:
                if item not in seen:
                    item_counts[item] += 1
                    seen.add(item)

        frequent_items = [
            item for item, count in item_counts.items()
            if count >= min_count
        ]

        def _recurse(prefix: List[str], projected_db: List[List[str]]):
            if len(prefix) >= self._max_pattern_len:
                return

            # Count items that appear after the prefix in each sequence
            next_counts: Dict[str, int] = defaultdict(int)
            next_projected: Dict[str, List[List[str]]] = defaultdict(list)

            for seq in projected_db:
                seen_in_seq: Set[str] = set()
                for i, item in enumerate(seq):
                    if item not in seen_in_seq:
                        next_counts[item] += 1
                        seen_in_seq.add(item)
                        next_projected[item].append(seq[i + 1:])

            for item, count in next_counts.items():
                if count >= min_count:
                    new_prefix = prefix + [item]
                    support = count / n_sequences
                    results.append((new_prefix, support))
                    _recurse(new_prefix, next_projected[item])

        # Build initial projected databases
        for item in frequent_items:
            prefix = [item]
            support = item_counts[item] / n_sequences
            results.append((prefix, support))

            projected_db = []
            for seq in sequences:
                for i, s in enumerate(seq):
                    if s == item:
                        projected_db.append(seq[i + 1:])
                        break

            _recurse(prefix, projected_db)

        # Sort by pattern length (longer = more specific) then support
        results.sort(key=lambda x: (len(x[0]), x[1]), reverse=True)
        return results

    # ------------------------------------------------------------------
    # Sequence building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_sequences(students: list) -> List[List[str]]:
        """Build ordered course sequences from passed subjects, grouped by semester."""
        sequences = []
        for st in students:
            completed = st.get("completed_subjects", [])
            passed = [s for s in completed if s.get("status") == "Passed"]
            if not passed:
                continue

            # Sort by semester then subject_id for stability
            sorted_subs = sorted(
                passed,
                key=lambda s: (s.get("semester", ""), s["subject_id"]),
            )
            seq = [s["subject_id"] for s in sorted_subs]
            if seq:
                sequences.append(seq)
        return sequences

    @staticmethod
    def _build_student_sequence(completed: list) -> List[str]:
        """Build the current student's ordered sequence of passed courses."""
        passed = [s for s in completed if s.get("status") == "Passed"]
        sorted_subs = sorted(
            passed,
            key=lambda s: (s.get("semester", ""), s["subject_id"]),
        )
        return [s["subject_id"] for s in sorted_subs]

    @staticmethod
    def _longest_prefix_match(student_seq: List[str], pattern: List[str]) -> int:
        """Find the longest prefix of pattern that appears as a subsequence in student_seq."""
        student_set = set(student_seq)
        matched = 0
        for item in pattern:
            if item in student_set:
                matched += 1
            else:
                break
        return matched

    # ------------------------------------------------------------------
    # Course statistics
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_course_stats(students: list) -> Dict[str, Dict]:
        """Compute per-course statistics from all student records."""
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
        pattern_count: int,
    ) -> str:
        parts = []
        if is_core:
            parts.append("Core curriculum course.")
        else:
            parts.append("Elective course.")

        if pattern_count > 0:
            parts.append(
                f"Appears in {pattern_count} successful student sequence pattern(s)."
            )
        else:
            parts.append("Recommended based on academic relevance.")

        parts.append(f"Historical pass rate: {p_pass:.0%}.")
        parts.append(f"Overall recommendation score: {final_score:.0%}.")
        return " ".join(parts)

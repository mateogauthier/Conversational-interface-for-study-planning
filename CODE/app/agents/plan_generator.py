"""Study plan generation algorithm.

Pure Python module for generating semester-by-semester study plans.
Prevents LLM hallucinations by using deterministic course selection.
"""

import math
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Constants
MIN_CREDITS_PER_SEMESTER = 12
MAX_CREDITS_PER_SEMESTER = 20
RECOMMENDED_CREDITS = 15
MAX_SEMESTERS = 20  # Safety limit to prevent infinite loops


def generate_study_plan(
    schooling: Dict,
    curriculum: Dict,
    target_graduation: Optional[str] = None,
    credits_preference: int = 15,
    include_electives: bool = True,
    prioritize_early: bool = False
) -> Dict:
    """Generate a complete semester-by-semester study plan.

    This is a pure Python function with deterministic behavior.
    It NEVER invents courses - only uses courses from the curriculum.

    Args:
        schooling: Student's academic history with completed/in-progress courses
        curriculum: Degree curriculum with all available courses
        target_graduation: Target graduation semester (e.g., "2027-2") or None
        credits_preference: Preferred credits per semester (12-20)
        include_electives: Whether to include elective courses
        prioritize_early: Maximize credits to graduate faster

    Returns:
        Dict with success status, semester plans, and metadata
    """
    logger.info("Starting study plan generation")

    # Validate inputs
    if not schooling or not curriculum:
        return {
            "success": False,
            "error": "Missing required data (schooling or curriculum)"
        }

    # Clamp credits preference to valid range
    credits_preference = max(MIN_CREDITS_PER_SEMESTER, min(credits_preference, MAX_CREDITS_PER_SEMESTER))

    # Extract student progress
    completed_subjects = schooling.get("completed_subjects", [])
    in_progress_subjects = schooling.get("in_progress_subjects", [])
    current_semester = schooling.get("current_semester", "2025-1")

    completed_ids = {s["subject_id"] for s in completed_subjects}
    in_progress_ids = {s["subject_id"] for s in in_progress_subjects}

    logger.info(f"Student has completed {len(completed_ids)} courses, {len(in_progress_ids)} in progress")

    # Flatten curriculum into course list
    all_courses = []
    for semester_data in curriculum.get("curriculum", []):
        for course in semester_data.get("subjects", []):
            all_courses.append(course)

    logger.info(f"Total courses in curriculum: {len(all_courses)}")

    # Filter remaining courses (not completed or in progress)
    remaining_courses = [
        c for c in all_courses
        if c["subject_id"] not in (completed_ids | in_progress_ids)
    ]

    # Filter electives if requested
    if not include_electives:
        before_count = len(remaining_courses)
        remaining_courses = [c for c in remaining_courses if not c.get("is_elective", False)]
        logger.info(f"Excluded {before_count - len(remaining_courses)} elective courses")

    if not remaining_courses:
        return {
            "success": True,
            "message": "All courses completed - no plan needed",
            "semester_plans": [],
            "total_semesters": 0,
            "total_remaining_credits": 0,
            "estimated_graduation": current_semester,
            "summary": {
                "courses_planned": 0,
                "average_credits_per_semester": 0,
                "total_credits_planned": 0
            },
            "warnings": []
        }

    total_remaining_credits = sum(c.get("credits", 0) for c in remaining_courses)
    logger.info(f"Remaining: {len(remaining_courses)} courses, {total_remaining_credits} credits")

    # Calculate or validate target graduation
    if target_graduation:
        semesters_available = count_semesters_between(current_semester, target_graduation)
        min_semesters_needed = math.ceil(total_remaining_credits / MAX_CREDITS_PER_SEMESTER)

        if semesters_available < min_semesters_needed:
            recommended_semester = calculate_semester_from_now(current_semester, min_semesters_needed)
            return {
                "success": False,
                "error": "Target graduation not feasible",
                "message": f"You need at least {min_semesters_needed} semesters to complete {total_remaining_credits} credits. Target {target_graduation} only allows {semesters_available} semesters.",
                "recommendation": f"Consider extending graduation to {recommended_semester}",
                "details": {
                    "semesters_available": semesters_available,
                    "min_semesters_needed": min_semesters_needed,
                    "total_credits_remaining": total_remaining_credits
                }
            }
    else:
        # Auto-calculate target graduation
        semesters_needed = math.ceil(total_remaining_credits / credits_preference)
        target_graduation = calculate_semester_from_now(current_semester, semesters_needed)
        logger.info(f"Auto-calculated target graduation: {target_graduation}")

    # Generate plan semester by semester
    semester_plans = []
    simulated_completed = completed_ids.copy()
    current_sem = increment_semester(current_semester)  # Start from next semester
    warnings = []
    iteration = 0

    logger.info("Beginning semester-by-semester planning")

    while remaining_courses and iteration < MAX_SEMESTERS:
        iteration += 1
        logger.info(f"\nPlanning semester {current_sem} (iteration {iteration})")

        # Get courses available this semester (prerequisites met)
        available = filter_by_prerequisites(remaining_courses, simulated_completed)

        logger.info(f"  Available courses: {len(available)}")

        if not available:
            if remaining_courses:
                # Deadlock - courses remain but none available
                msg = f"Prerequisite deadlock at semester {current_sem}: {len(remaining_courses)} courses remain but prerequisites cannot be satisfied"
                logger.warning(msg)
                warnings.append(msg)

                # List the blocked courses for debugging
                blocked_courses = [c["subject_id"] for c in remaining_courses]
                logger.warning(f"  Blocked courses: {blocked_courses}")
                break
            else:
                logger.info("No more courses - plan complete")
                break

        # Select courses for this semester using priority algorithm
        selected_courses = select_courses_for_semester(
            available,
            credits_preference,
            prioritize_early,
            simulated_completed,
            all_courses
        )

        if not selected_courses:
            msg = f"No courses could be selected for {current_sem}"
            logger.warning(msg)
            warnings.append(msg)
            break

        total_credits = sum(c["credits"] for c in selected_courses)
        logger.info(f"  Selected {len(selected_courses)} courses for {total_credits} credits")

        # Create semester plan
        semester_plan = {
            "semester": current_sem,
            "planned_subjects": [
                {
                    "subject_id": c["subject_id"],
                    "subject_name": c.get("name", c["subject_id"]),
                    "credits": c["credits"],
                    "priority": "High" if not c.get("is_elective") else "Medium",
                    "notes": f"Prerequisites: {', '.join(c.get('prerequisites', []))}" if c.get("prerequisites") else None
                }
                for c in selected_courses
            ],
            "total_credits": total_credits,
            "notes": None
        }

        # Check for warnings
        if total_credits > 17:
            msg = f"{current_sem}: Heavy course load ({total_credits} credits)"
            logger.info(f"  Warning: {msg}")
            warnings.append(msg)
        elif total_credits < MIN_CREDITS_PER_SEMESTER:
            msg = f"{current_sem}: Below minimum full-time ({total_credits} credits)"
            logger.warning(f"  Warning: {msg}")
            warnings.append(msg)

        semester_plans.append(semester_plan)

        # Update simulation state for next iteration
        selected_ids = {c["subject_id"] for c in selected_courses}
        simulated_completed.update(selected_ids)
        remaining_courses = [c for c in remaining_courses if c["subject_id"] not in selected_ids]

        logger.info(f"  Remaining: {len(remaining_courses)} courses")

        # Move to next semester
        current_sem = increment_semester(current_sem)

        # Check if we've exceeded target graduation
        if target_graduation and current_sem > target_graduation:
            msg = f"Plan extends beyond target graduation ({target_graduation})"
            logger.warning(msg)
            warnings.append(msg)

    # Final checks
    if remaining_courses:
        msg = f"{len(remaining_courses)} courses could not be scheduled"
        logger.warning(msg)
        warnings.append(msg)

    if iteration >= MAX_SEMESTERS:
        msg = f"Plan generation stopped at iteration limit ({MAX_SEMESTERS} semesters)"
        logger.error(msg)
        warnings.append(msg)

    # Calculate summary statistics
    total_courses_planned = sum(len(sp["planned_subjects"]) for sp in semester_plans)
    total_credits_planned = sum(sp["total_credits"] for sp in semester_plans)
    avg_credits = round(total_credits_planned / len(semester_plans), 1) if semester_plans else 0

    logger.info(f"\nPlan generation complete:")
    logger.info(f"  Total semesters: {len(semester_plans)}")
    logger.info(f"  Total courses: {total_courses_planned}")
    logger.info(f"  Total credits: {total_credits_planned}")
    logger.info(f"  Average credits/semester: {avg_credits}")

    return {
        "success": True,
        "semester_plans": semester_plans,
        "total_semesters": len(semester_plans),
        "total_remaining_credits": total_remaining_credits,
        "estimated_graduation": semester_plans[-1]["semester"] if semester_plans else current_semester,
        "summary": {
            "courses_planned": total_courses_planned,
            "average_credits_per_semester": avg_credits,
            "total_credits_planned": total_credits_planned
        },
        "warnings": warnings
    }


def filter_by_prerequisites(courses: List[Dict], completed_ids: Set[str]) -> List[Dict]:
    """Filter courses to only those with all prerequisites met.

    Args:
        courses: List of course dictionaries
        completed_ids: Set of subject_ids that are considered completed

    Returns:
        List of courses with prerequisites satisfied
    """
    available = []

    for course in courses:
        prereqs = course.get("prerequisites", [])

        # Check if all prerequisites are met
        missing = [p for p in prereqs if p not in completed_ids]

        if not missing:
            available.append(course)

    return available


def select_courses_for_semester(
    available_courses: List[Dict],
    target_credits: int,
    prioritize_early: bool,
    completed_ids: Set[str],
    all_courses: List[Dict]
) -> List[Dict]:
    """Select optimal courses for a single semester using priority algorithm.

    Priority scoring:
    - Required courses: +1000 points
    - Blocks other courses (is a prerequisite): +100 points per blocked course
    - Earlier suggested semester: +10 points
    - Early graduation mode: +5 points per credit

    Args:
        available_courses: Courses available this semester (prerequisites met)
        target_credits: Target credits for semester
        prioritize_early: Whether to maximize credits for early graduation
        completed_ids: Set of already completed course IDs
        all_courses: All courses in curriculum (for dependency analysis)

    Returns:
        List of selected courses for the semester
    """
    if not available_courses:
        return []

    # Score each course
    scored = []
    for course in available_courses:
        score = 0

        # Required courses get highest priority
        if not course.get("is_elective", False):
            score += 1000

        # Courses that unblock others (are prerequisites) get priority
        blocks_count = count_courses_blocked_by(course["subject_id"], all_courses, completed_ids)
        score += blocks_count * 100

        # Earlier suggested semesters get priority
        suggested_sem = course.get("semester_offered", 999)
        if suggested_sem <= 10:
            score += (11 - suggested_sem) * 10

        # Early graduation mode: prefer higher credit courses
        if prioritize_early:
            score += course.get("credits", 0) * 5

        scored.append((score, course))

    # Sort by priority score (highest first)
    scored.sort(key=lambda x: x[0], reverse=True)

    # Pack semester using greedy knapsack approach
    selected = []
    total_credits = 0

    for score, course in scored:
        course_credits = course.get("credits", 0)

        # Try to add course if it fits
        if total_credits + course_credits <= MAX_CREDITS_PER_SEMESTER:
            selected.append(course)
            total_credits += course_credits

            # Stop if we've hit target and not prioritizing early graduation
            if not prioritize_early and total_credits >= target_credits and total_credits >= MIN_CREDITS_PER_SEMESTER:
                break

    return selected


def count_courses_blocked_by(subject_id: str, all_courses: List[Dict], completed_ids: Set[str]) -> int:
    """Count how many incomplete courses require this subject as a prerequisite.

    Args:
        subject_id: The subject to check
        all_courses: All courses in curriculum
        completed_ids: Set of already completed course IDs

    Returns:
        Number of incomplete courses that require this subject
    """
    count = 0
    for course in all_courses:
        if course["subject_id"] not in completed_ids:
            if subject_id in course.get("prerequisites", []):
                count += 1
    return count


def increment_semester(semester: str) -> str:
    """Increment semester by one (e.g., '2025-1' -> '2025-2' -> '2026-1').

    Args:
        semester: Semester string in format "YYYY-S"

    Returns:
        Next semester string
    """
    try:
        year, sem = semester.split("-")
        year, sem = int(year), int(sem)

        if sem == 1:
            return f"{year}-2"
        else:
            return f"{year+1}-1"
    except (ValueError, IndexError):
        logger.error(f"Invalid semester format: {semester}")
        return "2025-2"  # Fallback


def calculate_semester_from_now(current: str, num_semesters: int) -> str:
    """Calculate semester N semesters from current.

    Args:
        current: Current semester in format "YYYY-S"
        num_semesters: Number of semesters to advance

    Returns:
        Target semester string
    """
    result = current
    for _ in range(num_semesters):
        result = increment_semester(result)
    return result


def count_semesters_between(start: str, end: str) -> int:
    """Count number of semesters between two semester strings.

    Args:
        start: Start semester (e.g., "2025-1")
        end: End semester (e.g., "2027-2")

    Returns:
        Number of semesters between start and end (inclusive of end, exclusive of start)
    """
    try:
        start_year, start_sem = map(int, start.split("-"))
        end_year, end_sem = map(int, end.split("-"))

        # Calculate total semesters from a reference point
        start_total = start_year * 2 + start_sem
        end_total = end_year * 2 + end_sem

        return end_total - start_total
    except (ValueError, IndexError):
        logger.error(f"Invalid semester format: start={start}, end={end}")
        return 0


def validate_plan(plan: Dict, curriculum: Dict, schooling: Dict) -> List[str]:
    """Validate a generated study plan for correctness.

    Args:
        plan: Generated plan with semester_plans
        curriculum: Original curriculum
        schooling: Student's academic history

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not plan.get("success"):
        return ["Plan generation failed"]

    semester_plans = plan.get("semester_plans", [])

    if not semester_plans:
        return []  # Empty plan is valid (no courses remaining)

    # Flatten curriculum
    all_courses = []
    for semester_data in curriculum.get("curriculum", []):
        all_courses.extend(semester_data.get("subjects", []))

    curriculum_course_ids = {c["subject_id"] for c in all_courses}

    # Check each semester
    seen_courses = set()

    for sp in semester_plans:
        semester = sp.get("semester", "unknown")
        planned_subjects = sp.get("planned_subjects", [])

        # Check credit load
        total_credits = sp.get("total_credits", 0)
        if total_credits < MIN_CREDITS_PER_SEMESTER:
            errors.append(f"{semester}: Below minimum credits ({total_credits} < {MIN_CREDITS_PER_SEMESTER})")
        if total_credits > MAX_CREDITS_PER_SEMESTER:
            errors.append(f"{semester}: Exceeds maximum credits ({total_credits} > {MAX_CREDITS_PER_SEMESTER})")

        # Check each course
        for ps in planned_subjects:
            subject_id = ps.get("subject_id")

            # Course exists in curriculum?
            if subject_id not in curriculum_course_ids:
                errors.append(f"{semester}: Invalid course {subject_id} (not in curriculum)")

            # Duplicate course?
            if subject_id in seen_courses:
                errors.append(f"{semester}: Duplicate course {subject_id}")

            seen_courses.add(subject_id)

    return errors

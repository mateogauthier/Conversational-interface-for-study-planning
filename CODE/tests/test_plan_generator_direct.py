"""Direct test of plan generation algorithm without API calls."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.plan_generator import generate_study_plan

# Sample test data mimicking real API responses
sample_schooling = {
    "completed_subjects": [
        {"subject_id": "MAT101", "subject_name": "Calculus I", "credits": 8, "grade": 85.0, "status": "Passed"},
        {"subject_id": "PROG101", "subject_name": "Programming I", "credits": 8, "grade": 90.0, "status": "Passed"},
        {"subject_id": "FIS101", "subject_name": "Physics I", "credits": 6, "grade": 80.0, "status": "Passed"},
        {"subject_id": "INTRO101", "subject_name": "Introduction to Engineering", "credits": 4, "grade": 88.0, "status": "Passed"},
    ],
    "in_progress_subjects": [
        {"subject_id": "MAT102", "subject_name": "Calculus II", "credits": 8, "status": "In Progress"},
    ],
    "current_semester": "2025-1",
    "total_credits_earned": 26,
    "gpa": 85.75
}

sample_curriculum = {
    "degree_id": "CS-ENG-2024",
    "degree_name": "Computer Engineering",
    "total_credits": 100,  # Simplified for testing
    "curriculum": [
        {
            "semester": 1,
            "subjects": [
                {"subject_id": "MAT101", "name": "Calculus I", "credits": 8, "prerequisites": [], "is_elective": False, "semester_offered": 1},
                {"subject_id": "PROG101", "name": "Programming I", "credits": 8, "prerequisites": [], "is_elective": False, "semester_offered": 1},
                {"subject_id": "FIS101", "name": "Physics I", "credits": 6, "prerequisites": [], "is_elective": False, "semester_offered": 1},
                {"subject_id": "INTRO101", "name": "Introduction to Engineering", "credits": 4, "prerequisites": [], "is_elective": False, "semester_offered": 1},
            ]
        },
        {
            "semester": 2,
            "subjects": [
                {"subject_id": "MAT102", "name": "Calculus II", "credits": 8, "prerequisites": ["MAT101"], "is_elective": False, "semester_offered": 2},
                {"subject_id": "PROG102", "name": "Programming II", "credits": 8, "prerequisites": ["PROG101"], "is_elective": False, "semester_offered": 2},
                {"subject_id": "FIS102", "name": "Physics II", "credits": 6, "prerequisites": ["FIS101", "MAT101"], "is_elective": False, "semester_offered": 2},
                {"subject_id": "DS101", "name": "Data Structures", "credits": 8, "prerequisites": ["PROG101"], "is_elective": False, "semester_offered": 2},
            ]
        },
        {
            "semester": 3,
            "subjects": [
                {"subject_id": "ALG101", "name": "Algorithms", "credits": 8, "prerequisites": ["DS101", "MAT102"], "is_elective": False, "semester_offered": 3},
                {"subject_id": "DATABASE101", "name": "Database Systems", "credits": 8, "prerequisites": ["DS101"], "is_elective": False, "semester_offered": 3},
                {"subject_id": "WEB101", "name": "Web Development", "credits": 8, "prerequisites": ["PROG102"], "is_elective": False, "semester_offered": 3},
            ]
        },
        {
            "semester": 4,
            "subjects": [
                {"subject_id": "ML101", "name": "Machine Learning", "credits": 8, "prerequisites": ["ALG101"], "is_elective": True, "semester_offered": 4},
                {"subject_id": "SEC101", "name": "Cybersecurity", "credits": 8, "prerequisites": ["DATABASE101"], "is_elective": True, "semester_offered": 4},
            ]
        }
    ]
}


def test_basic_plan_generation():
    """Test basic plan generation with sample data."""
    print("\n" + "=" * 80)
    print("TEST 1: Basic Plan Generation")
    print("=" * 80)

    result = generate_study_plan(
        schooling=sample_schooling,
        curriculum=sample_curriculum,
        target_graduation=None,  # Auto-calculate
        credits_preference=15,
        include_electives=True,
        prioritize_early=False
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        print(f"📅 Total semesters: {result['total_semesters']}")
        print(f"🎓 Estimated graduation: {result['estimated_graduation']}")
        print(f"📚 Total credits to plan: {result['total_remaining_credits']}")
        print(f"📊 Summary: {result['summary']}")

        if result.get("warnings"):
            print(f"\n⚠️  Warnings:")
            for warning in result["warnings"]:
                print(f"   - {warning}")

        print(f"\n📋 Semester Breakdown:")
        for sp in result["semester_plans"]:
            print(f"\n   {sp['semester']} ({sp['total_credits']} credits):")
            for ps in sp["planned_subjects"]:
                prereqs = f" [prereqs: {ps.get('notes', 'None')}]" if ps.get('notes') else ""
                print(f"      • {ps['subject_id']}: {ps['subject_name']} ({ps['credits']} credits){prereqs}")
    else:
        print(f"❌ Error: {result.get('error')}")
        print(f"   Message: {result.get('message', 'N/A')}")

    return result


def test_prerequisite_blocking():
    """Test that prerequisites are correctly validated."""
    print("\n" + "=" * 80)
    print("TEST 2: Prerequisite Blocking")
    print("=" * 80)

    # Student has completed nothing
    empty_schooling = {
        "completed_subjects": [],
        "in_progress_subjects": [],
        "current_semester": "2025-1",
        "total_credits_earned": 0,
        "gpa": 0.0
    }

    result = generate_study_plan(
        schooling=empty_schooling,
        curriculum=sample_curriculum,
        credits_preference=15,
        include_electives=True,
        prioritize_early=False
    )

    print(f"\n✅ Success: {result.get('success')}")

    if result.get("success"):
        # Check that semester 1 only has courses with no prerequisites
        semester_1 = result["semester_plans"][0]
        print(f"\n📋 Semester 1 courses (should have no prerequisites):")
        for ps in semester_1["planned_subjects"]:
            # Find the course in curriculum
            for sem_data in sample_curriculum["curriculum"]:
                for course in sem_data["subjects"]:
                    if course["subject_id"] == ps["subject_id"]:
                        prereqs = course.get("prerequisites", [])
                        print(f"   • {ps['subject_id']}: Prerequisites = {prereqs}")
                        if prereqs:
                            print(f"      ⚠️  WARNING: Course has prerequisites but is in first semester!")

        # Check that semester 2 respects prerequisites from semester 1
        if len(result["semester_plans"]) > 1:
            semester_2 = result["semester_plans"][1]
            completed_in_sem1 = {ps["subject_id"] for ps in semester_1["planned_subjects"]}

            print(f"\n📋 Semester 2 courses (prerequisites should be met):")
            for ps in semester_2["planned_subjects"]:
                for sem_data in sample_curriculum["curriculum"]:
                    for course in sem_data["subjects"]:
                        if course["subject_id"] == ps["subject_id"]:
                            prereqs = course.get("prerequisites", [])
                            missing = [p for p in prereqs if p not in completed_in_sem1]
                            print(f"   • {ps['subject_id']}: Prerequisites = {prereqs}")
                            if missing:
                                print(f"      ❌ ERROR: Missing prerequisites: {missing}")
                            else:
                                print(f"      ✅ All prerequisites met")
    else:
        print(f"❌ Error: {result.get('error')}")

    return result


def test_impossible_target():
    """Test error handling for impossible graduation target."""
    print("\n" + "=" * 80)
    print("TEST 3: Impossible Graduation Target")
    print("=" * 80)

    # Try to graduate in 1 semester with lots of credits remaining
    empty_schooling = {
        "completed_subjects": [],
        "in_progress_subjects": [],
        "current_semester": "2025-1",
        "total_credits_earned": 0,
        "gpa": 0.0
    }

    result = generate_study_plan(
        schooling=empty_schooling,
        curriculum=sample_curriculum,
        target_graduation="2025-2",  # Next semester (impossible)
        credits_preference=15,
        include_electives=True,
        prioritize_early=False
    )

    print(f"\n✅ Success: {result.get('success')}")

    if not result.get("success"):
        print(f"❌ Error (expected): {result.get('error')}")
        print(f"   Message: {result.get('message', 'N/A')}")
        print(f"   Recommendation: {result.get('recommendation', 'N/A')}")
        print(f"   Details: {result.get('details', {})}")
        print("\n✅ Test passed - correctly detected impossible target")
    else:
        print("❌ Test failed - should have detected impossible target")

    return result


def test_all_courses_completed():
    """Test when student has completed all courses."""
    print("\n" + "=" * 80)
    print("TEST 4: All Courses Completed")
    print("=" * 80)

    # Student completed everything
    all_completed_schooling = {
        "completed_subjects": [
            {"subject_id": "MAT101", "credits": 8, "status": "Passed"},
            {"subject_id": "PROG101", "credits": 8, "status": "Passed"},
            {"subject_id": "FIS101", "credits": 6, "status": "Passed"},
            {"subject_id": "INTRO101", "credits": 4, "status": "Passed"},
            {"subject_id": "MAT102", "credits": 8, "status": "Passed"},
            {"subject_id": "PROG102", "credits": 8, "status": "Passed"},
            {"subject_id": "FIS102", "credits": 6, "status": "Passed"},
            {"subject_id": "DS101", "credits": 8, "status": "Passed"},
            {"subject_id": "ALG101", "credits": 8, "status": "Passed"},
            {"subject_id": "DATABASE101", "credits": 8, "status": "Passed"},
            {"subject_id": "WEB101", "credits": 8, "status": "Passed"},
            {"subject_id": "ML101", "credits": 8, "status": "Passed"},
            {"subject_id": "SEC101", "credits": 8, "status": "Passed"},
        ],
        "in_progress_subjects": [],
        "current_semester": "2027-1",
        "total_credits_earned": 100,
        "gpa": 90.0
    }

    result = generate_study_plan(
        schooling=all_completed_schooling,
        curriculum=sample_curriculum,
        credits_preference=15,
        include_electives=True,
        prioritize_early=False
    )

    print(f"\n✅ Success: {result.get('success')}")
    print(f"📋 Semester plans: {len(result.get('semester_plans', []))}")
    print(f"💬 Message: {result.get('message', 'N/A')}")

    if len(result.get('semester_plans', [])) == 0:
        print("\n✅ Test passed - correctly detected no courses remaining")
    else:
        print("❌ Test failed - should have detected all courses completed")

    return result


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("STUDY PLAN GENERATOR - DIRECT TESTS")
    print("=" * 80)

    # Run all tests
    test_basic_plan_generation()
    test_prerequisite_blocking()
    test_impossible_target()
    test_all_courses_completed()

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

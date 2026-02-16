"""Pre-process the anonymized CSV into structured JSON seed data files.

This is a developer tool that reads the ORT Licenciatura en Sistemas CSV
and generates 4 JSON files for auto-seeding MongoDB on startup.

Usage:
    python scripts/preprocess_csv_to_seed.py

Input:  seed_data/ANPlan2019_Anonimizado.csv
Output: seed_data/degree.json, subjects.json, users.json, student_schooling.json
"""

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Try to use bson for ObjectId generation; fall back to uuid-based hex if not available
try:
    from bson import ObjectId

    def generate_id():
        return str(ObjectId())
except ImportError:
    import uuid

    def generate_id():
        return uuid.uuid4().hex[:24]


# ============================================
# Constants
# ============================================

DEGREE_ID = "LIC-SIS-2019"

DEGREE = {
    "degree_id": DEGREE_ID,
    "degree_name": "Licenciatura en Sistemas",
    "university": "Universidad ORT Uruguay",
    "total_credits": 168,
    "duration_semesters": 8,
    "description": (
        "Licenciatura en Sistemas - Plan 2019. "
        "Titulo intermedio: Analista de Sistemas en Computacion (tras 5to semestre)."
    ),
    "department": "Facultad de Ingenieria",
    "metadata": {
        "plan_year": 2019,
        "intermediate_title": "Analista de Sistemas en Computacion",
        "intermediate_title_semester": 5,
    },
}

# 28 core subjects with semester placement and prerequisites (from ORT website)
CORE_SUBJECTS = {
    # Semester 1
    "1479": {"semester": 1, "prereqs": []},
    "7109": {"semester": 1, "prereqs": []},
    "7687": {"semester": 1, "prereqs": []},
    "6402": {"semester": 1, "prereqs": []},
    # Semester 2
    "1743": {"semester": 2, "prereqs": ["1479"]},
    "7698": {"semester": 2, "prereqs": ["7109"]},
    "6406": {"semester": 2, "prereqs": []},
    # Semester 3
    "1774": {"semester": 3, "prereqs": ["1743"]},
    "7669": {"semester": 3, "prereqs": ["1743"]},
    "7680": {"semester": 3, "prereqs": []},
    "3837": {"semester": 3, "prereqs": ["1743"]},
    # Semester 4
    "7697": {"semester": 4, "prereqs": ["7698"]},
    "3924": {"semester": 4, "prereqs": ["1774", "7669"]},
    "3836": {"semester": 4, "prereqs": ["7109"]},
    "3839": {"semester": 4, "prereqs": ["3837"]},
    # Semester 5
    "3838": {"semester": 5, "prereqs": ["7697"]},
    "7681": {"semester": 5, "prereqs": ["3836"]},
    "7655": {"semester": 5, "prereqs": ["7669"]},
    "6343": {"semester": 5, "prereqs": ["3924"]},
    "7699": {"semester": 5, "prereqs": []},
    # Semester 6
    "6498": {"semester": 6, "prereqs": ["3838", "6343"]},
    "7674": {"semester": 6, "prereqs": ["7669"]},
    "3842": {"semester": 6, "prereqs": ["3839"]},
    # Semester 7
    "7658": {"semester": 7, "prereqs": ["6343"]},
    "6411": {"semester": 7, "prereqs": []},
    # Semester 8
    "6415": {"semester": 8, "prereqs": ["6411"]},
    "3856": {"semester": 8, "prereqs": ["3842"]},
    "3861": {"semester": 8, "prereqs": []},
}

DEFAULT_CREDITS = 6


# ============================================
# Helper functions
# ============================================


def normalize_semester(period: str) -> str:
    """Convert semester period string to YYYY-S format.

    Examples:
        "Marzo-abril 2019"             -> "2019-1"
        "Agosto-setiembre 2020"        -> "2020-2"
        "Talleres febrero-marzo 2022"  -> "2022-1"
        "Talleres julio-agosto 2021"   -> "2021-2"
        "Marzo 2024-Proyecto semestral" -> "2024-1"
        "Agosto 2022-Proyecto semestral" -> "2022-2"
    """
    period = period.strip()
    year_match = re.search(r"(\d{4})", period)
    if not year_match:
        return "unknown"
    year = year_match.group(1)

    period_lower = period.lower()
    if any(k in period_lower for k in ["marzo", "febrero", "abril"]):
        return f"{year}-1"
    elif any(k in period_lower for k in ["agosto", "julio", "setiembre", "septiembre"]):
        return f"{year}-2"

    return f"{year}-1"  # fallback


def compute_letter_grade(grade: float) -> str:
    """Compute letter grade from numeric grade (0-100)."""
    if grade >= 90:
        return "A"
    elif grade >= 80:
        return "B"
    elif grade >= 70:
        return "C"
    elif grade >= 60:
        return "D"
    else:
        return "F"


def parse_timestamp(ts: str) -> str:
    """Parse CSV timestamp to ISO format string."""
    try:
        dt = datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M:%S.%f")
        return dt.isoformat()
    except ValueError:
        try:
            dt = datetime.strptime(ts.strip(), "%Y-%m-%d")
            return dt.isoformat()
        except ValueError:
            return datetime.utcnow().isoformat()


# ============================================
# Main processing
# ============================================


def read_csv(csv_path: str) -> list[dict]:
    """Read the CSV and return a list of parsed record dicts."""
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 14:
                continue
            records.append(
                {
                    "case_id": row[0].strip(),
                    "subject_code": row[8].strip(),
                    "subject_name": row[9].strip(),
                    "type": row[10].strip(),  # P or T
                    "status": row[11].strip(),  # APR, ELI, ABN, NSP, REV, AUS
                    "grade": int(row[12].strip()) if row[12].strip() else 0,
                    "semester_period": row[6].strip(),
                    "timestamp": row[2].strip(),
                }
            )
    return records


def extract_subjects(records: list[dict]) -> dict[str, str]:
    """Extract unique subject_code -> subject_name mapping from records."""
    subjects = {}
    for r in records:
        code = r["subject_code"]
        if code not in subjects:
            subjects[code] = r["subject_name"]
    return subjects


def build_subject_documents(subject_map: dict[str, str]) -> list[dict]:
    """Build DegreeSubjectInDB-compatible documents for all subjects."""
    now = datetime.utcnow().isoformat()
    docs = []
    for code, name in sorted(subject_map.items()):
        core = CORE_SUBJECTS.get(code)
        doc = {
            "degree_id": DEGREE_ID,
            "subject_id": code,
            "name": name,
            "credits": DEFAULT_CREDITS,
            "department": None,
            "description": None,
            "prerequisites": core["prereqs"] if core else [],
            "corequisites": [],
            "semester_offered": core["semester"] if core else 0,
            "is_elective": core is None,
            "syllabus_url": None,
            "created_at": now,
            "updated_at": now,
            "metadata": {},
        }
        docs.append(doc)
    return docs


def determine_subject_outcome(subject_records: list[dict]) -> dict:
    """Determine the final outcome for one student+subject from all records.

    Rules:
    - T:APR exists -> Passed (use most recent T:APR grade)
    - No T:APR, has failed T records -> Failed
    - Only P:APR, no T records -> In Progress
    - Only failed P records -> Failed
    - REV records are skipped
    """
    # Filter out REV records
    filtered = [r for r in subject_records if r["status"] != "REV"]
    if not filtered:
        filtered = subject_records  # fallback if all are REV

    # Sort by timestamp descending (most recent first)
    filtered.sort(key=lambda r: r["timestamp"], reverse=True)

    # Check for T:APR (definitive pass)
    t_apr = [r for r in filtered if r["type"] == "T" and r["status"] == "APR"]
    if t_apr:
        best = t_apr[0]
        return {
            "status": "Passed",
            "grade": best["grade"],
            "semester": normalize_semester(best["semester_period"]),
            "completion_date": parse_timestamp(best["timestamp"]),
        }

    # Check for failed T records
    t_failures = [
        r
        for r in filtered
        if r["type"] == "T" and r["status"] in ("ELI", "ABN", "NSP", "AUS")
    ]

    # Check for P:APR without matching T
    p_apr = [r for r in filtered if r["type"] == "P" and r["status"] == "APR"]

    if t_failures:
        latest = t_failures[0]
        status = "Dropped" if latest["status"] == "ABN" else "Failed"
        return {
            "status": status,
            "grade": latest["grade"],
            "semester": normalize_semester(latest["semester_period"]),
            "completion_date": parse_timestamp(latest["timestamp"]),
        }

    if p_apr:
        latest = p_apr[0]
        return {
            "status": "In Progress",
            "grade": latest["grade"],
            "semester": normalize_semester(latest["semester_period"]),
            "completion_date": None,
        }

    # Only failed P records
    p_failures = [
        r
        for r in filtered
        if r["type"] == "P" and r["status"] in ("ELI", "ABN", "NSP", "AUS")
    ]
    if p_failures:
        latest = p_failures[0]
        status = "Dropped" if latest["status"] == "ABN" else "Failed"
        return {
            "status": status,
            "grade": 0,
            "semester": normalize_semester(latest["semester_period"]),
            "completion_date": parse_timestamp(latest["timestamp"]),
        }

    # Fallback
    latest = filtered[0]
    return {
        "status": "Failed",
        "grade": 0,
        "semester": normalize_semester(latest["semester_period"]),
        "completion_date": parse_timestamp(latest["timestamp"]),
    }


def process_students(records: list[dict], subject_map: dict[str, str]) -> tuple:
    """Process all records into user documents and schooling documents.

    Returns (users_list, schooling_list).
    """
    # Group records by student
    by_student = defaultdict(list)
    for r in records:
        by_student[r["case_id"]].append(r)

    users = []
    schooling_records = []

    for case_id in sorted(by_student.keys(), key=lambda x: int(x)):
        student_records = by_student[case_id]
        user_oid = generate_id()
        auth0_id = f"csv_student|{case_id}"

        # Build user document
        user_doc = {
            "_id": user_oid,
            "auth0_id": auth0_id,
            "email": f"student_{case_id}@ort.edu.uy",
            "name": f"Estudiante {case_id}",
            "role": "student",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "statistics": {
                "total_uploads": 0,
                "total_queries": 0,
                "total_storage_bytes": 0,
                "last_activity": None,
            },
            "metadata": {"source": "csv_import", "case_id": case_id},
        }
        users.append(user_doc)

        # Group student records by subject
        by_subject = defaultdict(list)
        for r in student_records:
            by_subject[r["subject_code"]].append(r)

        completed = []
        in_progress = []

        for subj_code, subj_records in by_subject.items():
            outcome = determine_subject_outcome(subj_records)
            subj_name = subject_map.get(subj_code, subj_code)

            # Count attempts (unique semester periods for this subject)
            semesters_seen = set()
            for sr in subj_records:
                semesters_seen.add(normalize_semester(sr["semester_period"]))
            attempt_number = max(1, len(semesters_seen))

            record = {
                "subject_id": subj_code,
                "subject_name": subj_name,
                "credits": DEFAULT_CREDITS,
                "grade": float(outcome["grade"]) if outcome["grade"] else None,
                "letter_grade": (
                    compute_letter_grade(outcome["grade"])
                    if outcome["grade"]
                    else None
                ),
                "status": outcome["status"],
                "semester": outcome["semester"],
                "attempt_number": attempt_number,
                "completion_date": outcome.get("completion_date"),
            }

            if outcome["status"] == "In Progress":
                in_progress.append(record)
            else:
                completed.append(record)

        # Calculate stats
        passed = [s for s in completed if s["status"] == "Passed"]
        total_credits_earned = sum(s["credits"] for s in passed)
        total_credits_attempted = sum(s["credits"] for s in completed)

        if passed:
            weighted_sum = sum(
                (s["grade"] or 0) * s["credits"] for s in passed
            )
            credit_sum = sum(s["credits"] for s in passed)
            gpa = round(weighted_sum / credit_sum, 2) if credit_sum > 0 else 0.0
        else:
            gpa = 0.0

        # Determine enrollment date (earliest record)
        all_timestamps = [r["timestamp"] for r in student_records]
        all_timestamps.sort()
        enrollment_date = parse_timestamp(all_timestamps[0])

        # Determine current semester (latest record)
        latest_semester = normalize_semester(
            max(student_records, key=lambda r: r["timestamp"])["semester_period"]
        )

        # Determine academic status
        core_codes = set(CORE_SUBJECTS.keys())
        passed_codes = set(s["subject_id"] for s in passed)
        all_core_passed = core_codes.issubset(passed_codes)
        academic_status = "Graduated" if all_core_passed else "Active"

        schooling_doc = {
            "degree_id": DEGREE_ID,
            "student_id": auth0_id,
            "user_id": user_oid,
            "enrollment_date": enrollment_date,
            "expected_graduation": None,
            "current_semester": latest_semester,
            "academic_status": academic_status,
            "completed_subjects": completed,
            "in_progress_subjects": in_progress,
            "total_credits_earned": total_credits_earned,
            "total_credits_attempted": total_credits_attempted,
            "gpa": gpa,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {"source": "csv_import", "case_id": case_id},
        }
        schooling_records.append(schooling_doc)

    return users, schooling_records


def main():
    # Resolve paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    seed_dir = project_root / "seed_data"
    csv_path = seed_dir / "ANPlan2019_Anonimizado.csv"

    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}")
        sys.exit(1)

    print(f"Reading CSV from {csv_path}...")
    records = read_csv(str(csv_path))
    print(f"  Parsed {len(records)} records")

    # Extract subjects
    subject_map = extract_subjects(records)
    print(f"  Found {len(subject_map)} unique subjects")

    # Build degree document
    now = datetime.utcnow().isoformat()
    degree_doc = {**DEGREE, "created_at": now, "updated_at": now}

    # Build subject documents
    subject_docs = build_subject_documents(subject_map)
    core_count = sum(1 for s in subject_docs if not s["is_elective"])
    elective_count = sum(1 for s in subject_docs if s["is_elective"])
    print(f"  Built {len(subject_docs)} subject documents ({core_count} core, {elective_count} elective)")

    # Process students
    print("Processing student records...")
    users, schooling = process_students(records, subject_map)
    print(f"  Built {len(users)} user documents")
    print(f"  Built {len(schooling)} schooling documents")

    # Stats
    passed_counts = []
    graduated = 0
    for s in schooling:
        passed = sum(1 for subj in s["completed_subjects"] if subj["status"] == "Passed")
        passed_counts.append(passed)
        if s["academic_status"] == "Graduated":
            graduated += 1

    avg_passed = sum(passed_counts) / len(passed_counts) if passed_counts else 0
    gpas = [s["gpa"] for s in schooling if s["gpa"] > 0]
    avg_gpa = sum(gpas) / len(gpas) if gpas else 0

    print(f"\n  Statistics:")
    print(f"    Avg passed subjects per student: {avg_passed:.1f}")
    print(f"    Avg GPA (students with grades): {avg_gpa:.1f}")
    print(f"    Graduated students: {graduated}")
    print(f"    Active students: {len(schooling) - graduated}")

    # Write JSON files
    seed_dir.mkdir(parents=True, exist_ok=True)

    degree_path = seed_dir / "degree.json"
    with open(degree_path, "w", encoding="utf-8") as f:
        json.dump(degree_doc, f, ensure_ascii=False, indent=2)
    print(f"\n  Wrote {degree_path} ({degree_path.stat().st_size} bytes)")

    subjects_path = seed_dir / "subjects.json"
    with open(subjects_path, "w", encoding="utf-8") as f:
        json.dump(subject_docs, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {subjects_path} ({subjects_path.stat().st_size} bytes)")

    users_path = seed_dir / "users.json"
    with open(users_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {users_path} ({users_path.stat().st_size} bytes)")

    schooling_path = seed_dir / "student_schooling.json"
    with open(schooling_path, "w", encoding="utf-8") as f:
        json.dump(schooling, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {schooling_path} ({schooling_path.stat().st_size} bytes)")

    print("\nDone! Seed data generated successfully.")


if __name__ == "__main__":
    main()

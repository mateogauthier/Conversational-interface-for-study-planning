"""Script to populate sample academic data for testing.

Run this script to add sample degrees, subjects, and student data to the database.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import mongodb
from app.services.academic_service import AcademicService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def populate_sample_data():
    """Populate database with sample academic data."""
    try:
        # Connect to database
        await mongodb.connect()
        db = mongodb.get_database()
        academic_service = AcademicService(db)

        logger.info("🎓 Starting academic data population...")

        # ============================================
        # Create Computer Engineering Degree
        # ============================================
        logger.info("\n📚 Creating Computer Engineering degree...")

        degree_data = {
            "degree_id": "CS-ENG-2024",
            "degree_name": "Computer Engineering",
            "university": "UNIVERSITY",
            "total_credits": 320,
            "duration_semesters": 10,
            "description": "Bachelor's degree in Computer Engineering",
            "department": "Computer Science & Engineering"
        }

        try:
            degree = await academic_service.create_degree(degree_data)
            logger.info(f"✅ Created degree: {degree.degree_name}")
        except Exception as e:
            logger.warning(f"⚠️  Degree may already exist: {e}")
            degree = await academic_service.get_degree("CS-ENG-2024")

        # ============================================
        # Create Subjects for the Degree
        # ============================================
        logger.info("\n📖 Creating subjects...")

        subjects = [
            # Semester 1
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "MAT101",
                "name": "Calculus I",
                "credits": 8,
                "department": "Mathematics",
                "description": "Differential calculus and applications",
                "prerequisites": [],
                "corequisites": [],
                "semester_offered": 1,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "PROG101",
                "name": "Programming I",
                "credits": 8,
                "department": "Computer Science",
                "description": "Introduction to programming with Python",
                "prerequisites": [],
                "corequisites": [],
                "semester_offered": 1,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "FIS101",
                "name": "Physics I",
                "credits": 6,
                "department": "Physics",
                "description": "Mechanics and thermodynamics",
                "prerequisites": [],
                "corequisites": ["MAT101"],
                "semester_offered": 1,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "INTRO101",
                "name": "Introduction to Engineering",
                "credits": 4,
                "department": "Engineering",
                "description": "Overview of engineering disciplines",
                "prerequisites": [],
                "corequisites": [],
                "semester_offered": 1,
                "is_elective": False
            },

            # Semester 2
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "MAT102",
                "name": "Calculus II",
                "credits": 8,
                "department": "Mathematics",
                "description": "Integral calculus and series",
                "prerequisites": ["MAT101"],
                "corequisites": [],
                "semester_offered": 2,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "PROG102",
                "name": "Programming II",
                "credits": 8,
                "department": "Computer Science",
                "description": "Data structures and algorithms",
                "prerequisites": ["PROG101"],
                "corequisites": [],
                "semester_offered": 2,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "FIS102",
                "name": "Physics II",
                "credits": 6,
                "department": "Physics",
                "description": "Electricity and magnetism",
                "prerequisites": ["FIS101"],
                "corequisites": ["MAT102"],
                "semester_offered": 2,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "CHEM101",
                "name": "Chemistry",
                "credits": 6,
                "department": "Chemistry",
                "description": "General chemistry principles",
                "prerequisites": [],
                "corequisites": [],
                "semester_offered": 2,
                "is_elective": False
            },

            # Semester 3
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "MAT201",
                "name": "Linear Algebra",
                "credits": 6,
                "department": "Mathematics",
                "description": "Vectors, matrices, and linear transformations",
                "prerequisites": ["MAT102"],
                "corequisites": [],
                "semester_offered": 3,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "PROG201",
                "name": "Object-Oriented Programming",
                "credits": 8,
                "department": "Computer Science",
                "description": "OOP principles with Java",
                "prerequisites": ["PROG102"],
                "corequisites": [],
                "semester_offered": 3,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "ARCH101",
                "name": "Computer Architecture",
                "credits": 6,
                "department": "Computer Science",
                "description": "Digital logic and computer organization",
                "prerequisites": ["PROG101"],
                "corequisites": [],
                "semester_offered": 3,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "STAT101",
                "name": "Probability and Statistics",
                "credits": 6,
                "department": "Mathematics",
                "description": "Statistical methods and probability theory",
                "prerequisites": ["MAT102"],
                "corequisites": [],
                "semester_offered": 3,
                "is_elective": False
            },

            # Semester 4
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "DB101",
                "name": "Database Systems I",
                "credits": 8,
                "department": "Computer Science",
                "description": "Relational databases and SQL",
                "prerequisites": ["PROG102"],
                "corequisites": [],
                "semester_offered": 4,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "OS101",
                "name": "Operating Systems",
                "credits": 8,
                "department": "Computer Science",
                "description": "OS principles and system programming",
                "prerequisites": ["PROG201", "ARCH101"],
                "corequisites": [],
                "semester_offered": 4,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "NET101",
                "name": "Computer Networks",
                "credits": 6,
                "department": "Computer Science",
                "description": "Network protocols and architecture",
                "prerequisites": ["PROG102"],
                "corequisites": [],
                "semester_offered": 4,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "ALGO101",
                "name": "Algorithms and Complexity",
                "credits": 8,
                "department": "Computer Science",
                "description": "Algorithm design and analysis",
                "prerequisites": ["PROG102", "MAT201"],
                "corequisites": [],
                "semester_offered": 4,
                "is_elective": False
            },

            # Semester 5
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "WEB101",
                "name": "Web Development",
                "credits": 6,
                "department": "Computer Science",
                "description": "Modern web technologies and frameworks",
                "prerequisites": ["PROG201", "DB101"],
                "corequisites": [],
                "semester_offered": 5,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "AI101",
                "name": "Artificial Intelligence",
                "credits": 8,
                "department": "Computer Science",
                "description": "AI fundamentals and machine learning basics",
                "prerequisites": ["ALGO101", "STAT101"],
                "corequisites": [],
                "semester_offered": 5,
                "is_elective": False
            },
            {
                "degree_id": "CS-ENG-2024",
                "subject_id": "SE101",
                "name": "Software Engineering I",
                "credits": 8,
                "department": "Computer Science",
                "description": "Software development methodologies",
                "prerequisites": ["PROG201"],
                "corequisites": [],
                "semester_offered": 5,
                "is_elective": False
            },
        ]

        created_count = 0
        for subject_data in subjects:
            try:
                subject = await academic_service.create_degree_subject(subject_data)
                logger.info(f"  ✓ {subject.subject_id}: {subject.name}")
                created_count += 1
            except Exception as e:
                logger.debug(f"  ⊘ {subject_data['subject_id']} may already exist")

        logger.info(f"\n✅ Created/verified {created_count} subjects")

        # ============================================
        # Summary
        # ============================================
        logger.info("\n" + "="*50)
        logger.info("🎉 Academic data population complete!")
        logger.info("="*50)
        logger.info(f"Degrees: 1")
        logger.info(f"Subjects: {len(subjects)}")
        logger.info("\nYou can now:")
        logger.info("  - View degrees: GET /academic/degrees")
        logger.info("  - View subjects: GET /academic/degrees/CS-ENG-2024/subjects")
        logger.info("  - View curriculum: GET /academic/degrees/CS-ENG-2024/curriculum")
        logger.info("="*50)

    except Exception as e:
        logger.error(f"❌ Error populating data: {e}", exc_info=True)
        raise
    finally:
        await mongodb.disconnect()


if __name__ == "__main__":
    asyncio.run(populate_sample_data())

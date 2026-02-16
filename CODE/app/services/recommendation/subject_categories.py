"""Subject-to-category mapping for ORT Uruguay – Licenciatura en Sistemas 2019.

Categories group subjects by academic discipline so the recommendation
model can learn per-category success patterns (SSRC feature).
"""

SUBJECT_CATEGORY = {
    # Programming
    "1479": "Programming",          # Programming 1
    "1743": "Programming",          # Programming 2
    "7107": "Programming",          # Programming Workshop
    "6498": "Programming",          # Network Programming
    "5640": "Programming",          # Game Programming
    "8382": "Programming",          # Blockchain Smart Contract Programming

    # Data Structures & Algorithms
    "1774": "Algorithms",           # Data Structures and Algorithms 1
    "1778": "Algorithms",           # Data Structures and Algorithms 2

    # Mathematics & Statistics
    "7109": "Mathematics",          # Fundamentals of Mathematics
    "7698": "Mathematics",          # Logic and Discrete Mathematics
    "3836": "Mathematics",          # Applied Probability and Statistics
    "7681": "Mathematics",          # Quantitative Methods for Business

    # Databases
    "3837": "Databases",            # Databases 1
    "3839": "Databases",            # Databases 2
    "3842": "Databases",            # Databases 3
    "7466": "Databases",            # Non-relational Databases
    "8558": "Databases",            # Analytics for Data Warehousing

    # Software Engineering
    "7669": "Software Engineering", # Fundamentals of Software Engineering
    "6410": "Software Engineering", # Software Engineering 2
    "7674": "Software Engineering", # Agile Software Engineering 1
    "7675": "Software Engineering", # Agile Software Engineering 2
    "3904": "Software Engineering", # Software Quality
    "6456": "Software Engineering", # Engineering Methods

    # Software Architecture & Design
    "3851": "Architecture",         # Software Architecture
    "3924": "Architecture",         # Application Design 1
    "6343": "Architecture",         # Application Design 2
    "7658": "Architecture",         # Enterprise Architectures
    "7902": "Architecture",         # Serverless Architectures
    "7655": "Architecture",         # Functional Analysis and Design

    # Infrastructure & Networks
    "3838": "Infrastructure",       # Networks
    "7697": "Infrastructure",       # Infrastructure
    "8455": "Infrastructure",       # Cloud Infrastructure 1

    # Security
    "6147": "Security",             # Application Security
    "7699": "Security",             # IT Security Workshop

    # AI & Data Science
    "3876": "AI & Data Science",    # Artificial Intelligence
    "7349": "AI & Data Science",    # Machine Learning for Intelligent Systems
    "7678": "AI & Data Science",    # Machine Learning for Data Analysis
    "3437": "AI & Data Science",    # Web Mining
    "7664": "AI & Data Science",    # Data Mining
    "7715": "AI & Data Science",    # Big Data Software Tools
    "3856": "AI & Data Science",    # Decision Support Systems
    "7894": "AI & Data Science",    # Data Visualization and Storytelling Workshop

    # UX & HCI
    "5327": "UX & Design",         # Interface Design
    "7667": "UX & Design",         # User-Centered Design
    "7676": "UX & Design",         # Human-Computer Interaction

    # Business & Management
    "6402": "Business",             # General Administration
    "6406": "Business",             # Information Systems Fundamentals
    "6414": "Business",             # Information Systems
    "6415": "Business",             # Business Strategy
    "6417": "Business",             # Organizational Behavior
    "6411": "Business",             # Finance and Project Valuation
    "3844": "Business",             # Operations Management
    "6852": "Business",             # Dynamic Entrepreneurship
    "6934": "Business",             # Disruptive Innovation
    "7680": "Business",             # Marketing, Markets and Digital Products
    "8058": "Business",             # Digital Transformation
    "8548": "Business",             # Business Process Improvement Workshop
    "7893": "Business",             # Organizational Reengineering Workshop

    # Project Management & Soft Skills
    "5636": "Project Management",   # Project Communication and Conflict Management
    "5733": "Project Management",   # Managerial Skills for Project Groups
    "5906": "Project Management",   # Team Skills in Software Development
    "7473": "Project Management",   # Negotiation Techniques for Project Teams
    "7663": "Project Management",   # Communication and Leadership
    "7686": "Project Management",   # Innovation and Entrepreneurship Workshop

    # Game Development
    "4784": "Game Development",     # Video Game Development 1
    "4872": "Game Development",     # Video Game Development 2

    # Emerging Tech
    "7472": "Emerging Tech",        # Connecting Things (IoT)
    "7716": "Emerging Tech",        # Blockchain Technologies for Smart Contracts

    # Research & Professional
    "6107": "Professional",         # IT-based Service Management
    "6110": "Professional",         # Research Methodology
    "7108": "Professional",         # Ethics, Law and Professional Communication
    "4891": "Professional",         # Research Project 1
    "3861": "Professional",         # Capstone Project

    # Technologies
    "7687": "Technologies",         # Technologies Workshop 1
    "7666": "Technologies",         # Technology-based Product Development
}

# Fallback for any subjects not explicitly mapped
DEFAULT_CATEGORY = "General"


def get_category(subject_id: str) -> str:
    """Return the category for a subject, with a safe fallback."""
    return SUBJECT_CATEGORY.get(subject_id, DEFAULT_CATEGORY)

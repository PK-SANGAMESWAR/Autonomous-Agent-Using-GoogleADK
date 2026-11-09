"""Dummy SQLite database of students, courses, enrollments and refunds for the refund agent."""

import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "refund.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students (id),
    course_id INTEGER NOT NULL REFERENCES courses (id),
    purchase_date TEXT NOT NULL,
    completion_percent REAL NOT NULL,
    UNIQUE (student_id, course_id)
);

-- One refund per enrollment. Saved as 'pending' once the student gives a reason
-- and confirms the amount, then set to 'processed' (with the payment provider's
-- transaction_id) or 'failed' after the refund call.
CREATE TABLE IF NOT EXISTS refunds (
    id INTEGER PRIMARY KEY,
    enrollment_id INTEGER NOT NULL UNIQUE REFERENCES enrollments (id),
    reason TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processed', 'failed')),
    transaction_id TEXT,
    requested_at TEXT NOT NULL,
    processed_at TEXT
);
"""

STUDENTS = [
    (1, "Aarav Sharma", "aarav.sharma@example.com"),
    (2, "Priya Nair", "priya.nair@example.com"),
    (3, "Rohan Mehta", "rohan.mehta@example.com"),
    (4, "Sneha Iyer", "sneha.iyer@example.com"),
    (5, "Karan Patel", "karan.patel@example.com"),
    (6, "Ananya Gupta", "ananya.gupta@example.com"),
]

# Prices in INR
COURSES = [
    (1, "Python for Beginners", 4999.0),
    (2, "Data Science with Pandas", 7999.0),
    (3, "Machine Learning Foundations", 9999.0),
    (4, "Kubernetes Essentials", 6499.0),
]

# (id, student_id, course_id, days since purchase, completion %)
ENROLLMENTS = [
    (1, 1, 1, 2, 10.0),   # eligible
    (2, 1, 2, 3, 60.0),   # too much completed
    (3, 2, 3, 5, 20.0),   # eligible at exactly 20%
    (4, 3, 1, 15, 5.0),   # purchased too long ago
    (5, 4, 4, 30, 85.0),  # fails both rules
    (6, 6, 2, 1, 0.0),    # eligible, not started
]
# Karan Patel (student 5) has no enrollments on purpose.


def create_database(db_path: Path = DB_PATH) -> None:
    """Create the tables and insert the dummy rows. Safe to run more than once."""
    today = date.today()
    enrollment_rows = [
        (id_, student_id, course_id, (today - timedelta(days=days)).isoformat(), completion)
        for id_, student_id, course_id, days, completion in ENROLLMENTS
    ]

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        conn.executemany("INSERT OR IGNORE INTO students VALUES (?, ?, ?)", STUDENTS)
        conn.executemany("INSERT OR IGNORE INTO courses VALUES (?, ?, ?)", COURSES)
        conn.executemany(
            "INSERT OR IGNORE INTO enrollments VALUES (?, ?, ?, ?, ?)", enrollment_rows
        )
    logger.info(f"Dummy refund database ready at {db_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_database()

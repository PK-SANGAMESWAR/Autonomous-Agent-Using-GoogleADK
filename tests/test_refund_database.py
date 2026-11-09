import sqlite3
from datetime import date

import pytest

from refund_agent import database


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "refund.db"
    database.create_database(db_path)
    connection = sqlite3.connect(db_path)
    yield connection
    connection.close()


def days_since(iso_date):
    return (date.today() - date.fromisoformat(iso_date)).days


def enrollments(conn):
    return conn.execute(
        "SELECT student_id, purchase_date, completion_percent FROM enrollments"
    ).fetchall()


def test_creates_separate_tables(conn):
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"students", "courses", "enrollments"} <= tables


def test_table_columns(conn):
    def columns(table):
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

    assert {"id", "name", "email"} <= columns("students")
    assert {"id", "title", "price"} <= columns("courses")
    assert {
        "id",
        "student_id",
        "course_id",
        "purchase_date",
        "completion_percent",
    } <= columns("enrollments")


def test_tables_have_dummy_rows(conn):
    for table in ("students", "courses", "enrollments"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count > 0, f"{table} is empty"


def test_student_emails_are_unique(conn):
    email = conn.execute("SELECT email FROM students LIMIT 1").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO students (name, email) VALUES (?, ?)", ("Copy", email)
        )


def test_enrollments_reference_existing_students_and_courses(conn):
    orphans = conn.execute(
        """
        SELECT COUNT(*) FROM enrollments e
        LEFT JOIN students s ON s.id = e.student_id
        LEFT JOIN courses c ON c.id = e.course_id
        WHERE s.id IS NULL OR c.id IS NULL
        """
    ).fetchone()[0]
    assert orphans == 0


def test_has_eligible_enrollment(conn):
    assert any(
        days_since(purchased) < 7 and completion < 20
        for _, purchased, completion in enrollments(conn)
    )


def test_has_eligible_enrollment_at_exactly_20_percent(conn):
    assert any(
        days_since(purchased) < 7 and completion == 20
        for _, purchased, completion in enrollments(conn)
    )


def test_has_enrollment_purchased_too_long_ago(conn):
    assert any(
        days_since(purchased) > 7 and completion <= 20
        for _, purchased, completion in enrollments(conn)
    )


def test_has_enrollment_with_too_much_completed(conn):
    assert any(
        days_since(purchased) < 7 and completion > 20
        for _, purchased, completion in enrollments(conn)
    )


def test_has_enrollment_failing_both_rules(conn):
    assert any(
        days_since(purchased) > 7 and completion > 20
        for _, purchased, completion in enrollments(conn)
    )


def test_has_student_with_several_enrollments(conn):
    most = conn.execute(
        "SELECT COUNT(*) FROM enrollments GROUP BY student_id ORDER BY 1 DESC LIMIT 1"
    ).fetchone()[0]
    assert most >= 2


def test_has_student_with_no_enrollments(conn):
    count = conn.execute(
        """
        SELECT COUNT(*) FROM students s
        WHERE NOT EXISTS (SELECT 1 FROM enrollments e WHERE e.student_id = s.id)
        """
    ).fetchone()[0]
    assert count >= 1


def test_running_twice_does_not_duplicate_rows(tmp_path):
    db_path = tmp_path / "refund.db"
    database.create_database(db_path)
    database.create_database(db_path)

    with sqlite3.connect(db_path) as connection:
        emails = [row[0] for row in connection.execute("SELECT email FROM students")]
    assert len(emails) == len(set(emails))
    assert len(emails) > 0


def test_has_refunds_table(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(refunds)")}
    assert {
        "id",
        "enrollment_id",
        "reason",
        "amount",
        "status",
        "transaction_id",
        "requested_at",
    } <= columns


def test_refunds_starts_empty_and_allows_one_per_enrollment(conn):
    assert conn.execute("SELECT COUNT(*) FROM refunds").fetchone()[0] == 0
    row = (1, "reason", 4999.0, "processed", "MOCK-1", "2026-01-01T00:00:00")
    sql = (
        "INSERT INTO refunds (enrollment_id, reason, amount, status, transaction_id, requested_at)"
        " VALUES (?, ?, ?, ?, ?, ?)"
    )
    conn.execute(sql, row)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, row)

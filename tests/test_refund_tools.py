import sqlite3
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from refund_agent import database, tools

AARAV = "aarav.sharma@example.com"  # enrollments 1 (eligible), 2 (too much completed)
PRIYA = "priya.nair@example.com"  # enrollment 3 (exactly 20%)
ROHAN = "rohan.mehta@example.com"  # enrollment 4 (purchased too long ago)
SNEHA = "sneha.iyer@example.com"  # enrollment 5 (fails both rules)
KARAN = "karan.patel@example.com"  # no enrollments


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "refund.db"
    database.create_database(path)
    monkeypatch.setattr(tools, "DB_PATH", path)
    return path


@pytest.fixture
def ctx():
    """Stand-in for ADK's ToolContext: tools only use its session `state`."""
    return SimpleNamespace(state={})


def login(ctx, email):
    result = tools.identify_student(email, ctx)
    assert result["status"] == "success"
    return ctx


def add_enrollment(db_path, student_id, course_id, days_ago, completion):
    purchased = (date.today() - timedelta(days=days_ago)).isoformat()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO enrollments (student_id, course_id, purchase_date, completion_percent)"
            " VALUES (?, ?, ?, ?)",
            (student_id, course_id, purchased, completion),
        )
        return cursor.lastrowid


def refund_rows(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT enrollment_id, reason, amount, status FROM refunds").fetchall()


# --- identify_student ---------------------------------------------------------


def test_identify_student_finds_registered_email(db_path, ctx):
    result = tools.identify_student(AARAV, ctx)

    assert result["status"] == "success"
    assert result["name"] == "Aarav Sharma"
    assert ctx.state["student_id"] == 1


def test_identify_student_ignores_case_and_spaces(db_path, ctx):
    result = tools.identify_student("  Aarav.Sharma@Example.COM ", ctx)

    assert result["status"] == "success"
    assert ctx.state["student_id"] == 1


def test_identify_student_unknown_email(db_path, ctx):
    result = tools.identify_student("nobody@example.com", ctx)

    assert result["status"] == "error"
    assert "nobody@example.com" in result["error_message"]
    assert ctx.state.get("student_id") is None


def test_identify_student_unknown_email_clears_previous_student(db_path, ctx):
    login(ctx, AARAV)

    tools.identify_student("nobody@example.com", ctx)

    assert ctx.state.get("student_id") is None


# --- get_my_enrollments -------------------------------------------------------


def test_get_my_enrollments_requires_identification(db_path, ctx):
    result = tools.get_my_enrollments(ctx)

    assert result["status"] == "error"


def test_get_my_enrollments_lists_all_courses(db_path, ctx):
    result = tools.get_my_enrollments(login(ctx, AARAV))

    assert result["status"] == "success"
    by_id = {e["enrollment_id"]: e for e in result["enrollments"]}
    assert set(by_id) == {1, 2}
    assert by_id[1]["course_title"] == "Python for Beginners"
    assert by_id[1]["price"] == 4999.0
    assert by_id[1]["completion_percent"] == 10.0
    assert "purchase_date" in by_id[1]


def test_get_my_enrollments_student_with_none(db_path, ctx):
    result = tools.get_my_enrollments(login(ctx, KARAN))

    assert result["status"] == "error"
    assert "no enrollments" in result["error_message"].lower()


# --- get_refund_policy --------------------------------------------------------


def test_get_refund_policy_reports_limits_from_constants():
    result = tools.get_refund_policy()

    assert result["status"] == "success"
    assert tools.MAX_DAYS_SINCE_PURCHASE == 7
    assert tools.MAX_COMPLETION_PERCENT == 20
    assert result["max_days_since_purchase"] == tools.MAX_DAYS_SINCE_PURCHASE
    assert result["max_completion_percent"] == tools.MAX_COMPLETION_PERCENT
    assert result["policy"]


# --- check_refund_eligibility -------------------------------------------------


def test_check_eligibility_requires_identification(db_path, ctx):
    assert tools.check_refund_eligibility(1, ctx)["status"] == "error"


def test_check_eligibility_rejects_another_students_enrollment(db_path, ctx):
    result = tools.check_refund_eligibility(3, login(ctx, AARAV))  # Priya's

    assert result["status"] == "error"


def test_check_eligibility_unknown_enrollment(db_path, ctx):
    assert tools.check_refund_eligibility(999, login(ctx, AARAV))["status"] == "error"


def test_check_eligibility_eligible(db_path, ctx):
    result = tools.check_refund_eligibility(1, login(ctx, AARAV))

    assert result["status"] == "success"
    assert result["eligible"] is True
    assert result["refund_amount"] == 4999.0
    assert result["days_since_purchase"] == 2
    assert result["reasons"] == []


def test_check_eligibility_exactly_20_percent_is_eligible(db_path, ctx):
    result = tools.check_refund_eligibility(3, login(ctx, PRIYA))

    assert result["eligible"] is True


def test_check_eligibility_too_long_ago(db_path, ctx):
    result = tools.check_refund_eligibility(4, login(ctx, ROHAN))

    assert result["eligible"] is False
    assert result["within_time_limit"] is False
    assert result["within_completion_limit"] is True
    assert len(result["reasons"]) == 1


def test_check_eligibility_too_much_completed(db_path, ctx):
    result = tools.check_refund_eligibility(2, login(ctx, AARAV))

    assert result["eligible"] is False
    assert result["within_time_limit"] is True
    assert result["within_completion_limit"] is False
    assert len(result["reasons"]) == 1


def test_check_eligibility_fails_both(db_path, ctx):
    result = tools.check_refund_eligibility(5, login(ctx, SNEHA))

    assert result["eligible"] is False
    assert result["within_time_limit"] is False
    assert result["within_completion_limit"] is False
    assert len(result["reasons"]) == 2


def test_check_eligibility_day_7_is_included(db_path, ctx):
    enrollment_id = add_enrollment(db_path, student_id=5, course_id=1, days_ago=7, completion=0)

    result = tools.check_refund_eligibility(enrollment_id, login(ctx, KARAN))

    assert result["eligible"] is True


def test_check_eligibility_day_8_is_too_late(db_path, ctx):
    enrollment_id = add_enrollment(db_path, student_id=5, course_id=1, days_ago=8, completion=0)

    result = tools.check_refund_eligibility(enrollment_id, login(ctx, KARAN))

    assert result["eligible"] is False


# --- request_refund -----------------------------------------------------------


def test_request_refund_processes_eligible_enrollment(db_path, ctx):
    result = tools.request_refund(1, "Course was too basic", login(ctx, AARAV))

    assert result["status"] == "success"
    assert result["refund_status"] == "processed"
    assert result["amount"] == 4999.0
    assert result["transaction_id"].startswith("MOCK-")
    assert refund_rows(db_path) == [(1, "Course was too basic", 4999.0, "processed")]


def test_request_refund_rechecks_eligibility(db_path, ctx):
    result = tools.request_refund(2, "Changed my mind", login(ctx, AARAV))

    assert result["status"] == "error"
    assert refund_rows(db_path) == []


def test_request_refund_requires_a_reason(db_path, ctx):
    result = tools.request_refund(1, "   ", login(ctx, AARAV))

    assert result["status"] == "error"
    assert refund_rows(db_path) == []


def test_request_refund_only_once_per_enrollment(db_path, ctx):
    login(ctx, AARAV)
    tools.request_refund(1, "Too basic", ctx)

    result = tools.request_refund(1, "Too basic", ctx)

    assert result["status"] == "error"
    assert "already" in result["error_message"].lower()
    assert len(refund_rows(db_path)) == 1


def test_request_refund_requires_identification(db_path, ctx):
    assert tools.request_refund(1, "Too basic", ctx)["status"] == "error"
    assert refund_rows(db_path) == []


def test_request_refund_rejects_another_students_enrollment(db_path, ctx):
    result = tools.request_refund(3, "Not mine", login(ctx, AARAV))  # Priya's

    assert result["status"] == "error"
    assert refund_rows(db_path) == []


# --- get_refund_status --------------------------------------------------------


def test_get_refund_status_after_request(db_path, ctx):
    login(ctx, AARAV)
    requested = tools.request_refund(1, "Too basic", ctx)

    result = tools.get_refund_status(1, ctx)

    assert result["status"] == "success"
    assert result["refund_status"] == "processed"
    assert result["amount"] == 4999.0
    assert result["reason"] == "Too basic"
    assert result["transaction_id"] == requested["transaction_id"]
    assert result["requested_at"]


def test_get_refund_status_without_request(db_path, ctx):
    result = tools.get_refund_status(1, login(ctx, AARAV))

    assert result["status"] == "error"


def test_get_refund_status_rejects_another_students_enrollment(db_path, ctx):
    login(ctx, PRIYA)
    tools.request_refund(3, "Too fast", ctx)

    result = tools.get_refund_status(3, login(ctx, AARAV))

    assert result["status"] == "error"

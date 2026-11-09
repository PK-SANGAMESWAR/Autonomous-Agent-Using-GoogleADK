"""Function tools for the refund agent. Each tool returns a dict with a "status" key.

The identified student is kept in the session state, so a student can only see
and refund their own enrollments.
"""

import logging
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime

from google.adk.tools import ToolContext

from refund_agent.database import DB_PATH, create_database

logger = logging.getLogger(__name__)

MAX_DAYS_SINCE_PURCHASE = 7  # day 7 itself is still eligible
MAX_COMPLETION_PERCENT = 20  # exactly 20% is still eligible
STUDENT_ID_KEY = "student_id"

NOT_IDENTIFIED = {
    "status": "error",
    "error_message": "Student not identified yet. Ask for their registered email and call identify_student.",
}


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Opens the database, commits on success and always closes the connection."""
    if not DB_PATH.exists():
        create_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _error(message: str) -> dict:
    return {"status": "error", "error_message": message}


def _find_enrollment(conn: sqlite3.Connection, enrollment_id: int, student_id: int):
    """Returns the enrollment joined with its course, only if it belongs to the student."""
    return conn.execute(
        """
        SELECT e.id, e.purchase_date, e.completion_percent, c.title, c.price
        FROM enrollments e JOIN courses c ON c.id = e.course_id
        WHERE e.id = ? AND e.student_id = ?
        """,
        (enrollment_id, student_id),
    ).fetchone()


def _evaluate(enrollment: sqlite3.Row) -> dict:
    """Applies the refund policy to one enrollment row."""
    days = (date.today() - date.fromisoformat(enrollment["purchase_date"])).days
    completion = enrollment["completion_percent"]
    within_time = days <= MAX_DAYS_SINCE_PURCHASE
    within_completion = completion <= MAX_COMPLETION_PERCENT

    reasons = []
    if not within_time:
        reasons.append(
            f"Purchased {days} days ago; refunds are only allowed within {MAX_DAYS_SINCE_PURCHASE} days of purchase."
        )
    if not within_completion:
        reasons.append(
            f"{completion:g}% of the course is completed; refunds are only allowed up to {MAX_COMPLETION_PERCENT}%."
        )

    return {
        "eligible": within_time and within_completion,
        "within_time_limit": within_time,
        "within_completion_limit": within_completion,
        "days_since_purchase": days,
        "completion_percent": completion,
        "reasons": reasons,
    }


def _issue_mock_payment_refund(enrollment_id: int, amount: float) -> str:
    """Stand-in for a real payment provider. Returns a transaction id."""
    transaction_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
    logger.info(f"Mock refund of INR {amount} for enrollment {enrollment_id}: {transaction_id}")
    return transaction_id


def identify_student(email: str, tool_context: ToolContext) -> dict:
    """Identifies the student by their registered email and remembers them for this conversation.

    Args:
        email: The student's registered email address.

    Returns:
        A dict with "status". On success also "student_id" and "name"; on error, "error_message".
    """
    normalized = email.strip().lower()
    with _connect() as conn:
        student = conn.execute(
            "SELECT id, name FROM students WHERE lower(email) = ?", (normalized,)
        ).fetchone()

    if student is None:
        tool_context.state[STUDENT_ID_KEY] = None
        return _error(f"No student is registered with the email '{normalized}'.")

    tool_context.state[STUDENT_ID_KEY] = student["id"]
    return {"status": "success", "student_id": student["id"], "name": student["name"]}


def get_my_enrollments(tool_context: ToolContext) -> dict:
    """Lists the identified student's course enrollments.

    Returns:
        A dict with "status". On success also "enrollments", a list of dicts with
        "enrollment_id", "course_title", "price", "purchase_date" and "completion_percent".
    """
    student_id = tool_context.state.get(STUDENT_ID_KEY)
    if student_id is None:
        return NOT_IDENTIFIED

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT e.id, c.title, c.price, e.purchase_date, e.completion_percent
            FROM enrollments e JOIN courses c ON c.id = e.course_id
            WHERE e.student_id = ? ORDER BY e.id
            """,
            (student_id,),
        ).fetchall()

    if not rows:
        return _error("This student has no enrollments, so there is nothing to refund.")

    return {
        "status": "success",
        "enrollments": [
            {
                "enrollment_id": row["id"],
                "course_title": row["title"],
                "price": row["price"],
                "purchase_date": row["purchase_date"],
                "completion_percent": row["completion_percent"],
            }
            for row in rows
        ],
    }


def get_refund_policy() -> dict:
    """Returns the course refund policy.

    Returns:
        A dict with "status", "policy" (plain-language text), "max_days_since_purchase"
        and "max_completion_percent".
    """
    return {
        "status": "success",
        "policy": (
            f"A full refund is given only if the request is made within {MAX_DAYS_SINCE_PURCHASE} days "
            f"of purchase AND at most {MAX_COMPLETION_PERCENT}% of the course is completed."
        ),
        "max_days_since_purchase": MAX_DAYS_SINCE_PURCHASE,
        "max_completion_percent": MAX_COMPLETION_PERCENT,
    }


def check_refund_eligibility(enrollment_id: int, tool_context: ToolContext) -> dict:
    """Checks whether one of the identified student's enrollments qualifies for a refund.

    Args:
        enrollment_id: The enrollment to check, from get_my_enrollments.

    Returns:
        A dict with "status". On success also "eligible", "within_time_limit",
        "within_completion_limit", "days_since_purchase", "completion_percent",
        "course_title", "refund_amount" and "reasons" (why it is not eligible; empty if eligible).
    """
    student_id = tool_context.state.get(STUDENT_ID_KEY)
    if student_id is None:
        return NOT_IDENTIFIED

    with _connect() as conn:
        enrollment = _find_enrollment(conn, enrollment_id, student_id)
    if enrollment is None:
        return _error(f"Enrollment {enrollment_id} was not found for this student.")

    return {
        "status": "success",
        "enrollment_id": enrollment_id,
        "course_title": enrollment["title"],
        "refund_amount": enrollment["price"],
        **_evaluate(enrollment),
    }


def request_refund(enrollment_id: int, reason: str, tool_context: ToolContext) -> dict:
    """Saves and processes a full refund. Only call after the student confirmed the amount.

    Eligibility is checked again here. The request is saved as "pending", sent to the
    payment provider, then marked "processed" (or "failed").

    Args:
        enrollment_id: The enrollment to refund.
        reason: The student's reason for the refund (kept as feedback).

    Returns:
        A dict with "status". On success also "refund_status", "amount" and "transaction_id".
    """
    student_id = tool_context.state.get(STUDENT_ID_KEY)
    if student_id is None:
        return NOT_IDENTIFIED
    if not reason.strip():
        return _error("A reason for the refund is required. Ask the student why they want a refund.")

    with _connect() as conn:
        enrollment = _find_enrollment(conn, enrollment_id, student_id)
        if enrollment is None:
            return _error(f"Enrollment {enrollment_id} was not found for this student.")

        evaluation = _evaluate(enrollment)
        if not evaluation["eligible"]:
            return _error("Not eligible for a refund: " + " ".join(evaluation["reasons"]))

        existing = conn.execute(
            "SELECT status FROM refunds WHERE enrollment_id = ?", (enrollment_id,)
        ).fetchone()
        if existing is not None:
            return _error(
                f"A refund was already requested for enrollment {enrollment_id} (status: {existing['status']})."
            )

        amount = enrollment["price"]
        conn.execute(
            "INSERT INTO refunds (enrollment_id, reason, amount, status, requested_at)"
            " VALUES (?, ?, ?, 'pending', ?)",
            (enrollment_id, reason.strip(), amount, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()

        try:
            transaction_id = _issue_mock_payment_refund(enrollment_id, amount)
        except Exception:
            logger.exception(f"Payment provider failed for enrollment {enrollment_id}")
            conn.execute("UPDATE refunds SET status = 'failed' WHERE enrollment_id = ?", (enrollment_id,))
            return _error("The payment provider could not process the refund. It has been recorded as failed.")

        conn.execute(
            "UPDATE refunds SET status = 'processed', transaction_id = ?, processed_at = ?"
            " WHERE enrollment_id = ?",
            (transaction_id, datetime.now().isoformat(timespec="seconds"), enrollment_id),
        )

    return {
        "status": "success",
        "enrollment_id": enrollment_id,
        "refund_status": "processed",
        "amount": amount,
        "transaction_id": transaction_id,
    }


def get_refund_status(enrollment_id: int, tool_context: ToolContext) -> dict:
    """Looks up the refund request for one of the identified student's enrollments.

    Args:
        enrollment_id: The enrollment whose refund to look up.

    Returns:
        A dict with "status". On success also "refund_status", "amount", "reason",
        "transaction_id", "requested_at" and "processed_at".
    """
    student_id = tool_context.state.get(STUDENT_ID_KEY)
    if student_id is None:
        return NOT_IDENTIFIED

    with _connect() as conn:
        refund = conn.execute(
            """
            SELECT r.status, r.amount, r.reason, r.transaction_id, r.requested_at, r.processed_at
            FROM refunds r JOIN enrollments e ON e.id = r.enrollment_id
            WHERE r.enrollment_id = ? AND e.student_id = ?
            """,
            (enrollment_id, student_id),
        ).fetchone()

    if refund is None:
        return _error(f"No refund request was found for enrollment {enrollment_id}.")

    return {
        "status": "success",
        "enrollment_id": enrollment_id,
        "refund_status": refund["status"],
        "amount": refund["amount"],
        "reason": refund["reason"],
        "transaction_id": refund["transaction_id"],
        "requested_at": refund["requested_at"],
        "processed_at": refund["processed_at"],
    }

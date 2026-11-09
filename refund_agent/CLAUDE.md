# refund_agent

## Purpose
Ed-tech companies sell courses, and students ask for refunds when they don't like a course or for other reasons. Today staff review these requests by hand. This agent automates the process end to end: it identifies the student, checks the request against the refund policy, and either processes the refund or explains why it can't.

## Refund policy
A student gets a **full refund** only when **both** conditions hold:
1. The request is made within **7 days** of purchase.
2. The student has completed **20% or less** of the course (exactly 20% is eligible).

If either condition fails, there is no refund, and the agent explains which condition failed.

## Conversation flow
See `FLOW.md` for the original notes.
1. **Identify:** ask for the student's registered email.
2. **Look up:** find the student and their course enrolment. If the email or enrolment isn't found, tell the student and stop.
3. **Check eligibility:** purchased within 7 days **and** completion ≤ 20%.
4. **If eligible:**
   1. Ask for the reason for the refund (kept as feedback).
   2. Confirm the refund amount (the full purchase price) with the student.
   3. Save the refund request.
   4. Issue the refund through the payment provider and confirm to the student that it's done.
5. **If not eligible:** explain why (too many days since purchase, too much of the course completed, or both).

## Open questions
- Is day 7 itself included, and is it counted from purchase or enrolment?
- If a student has several enrolments, how does the agent choose the course (ask the student, or list them)?
- Should enrolments store the amount actually paid and the original payment ID? A real payment provider needs the payment ID to refund, and discounts mean the amount paid can differ from the course price.
- Which payment provider issues the refund (start with a mock)?
- What should happen if the refund was already requested or processed for that enrolment?

## Current state
- `agent.py`: `root_agent` on `MODEL_NAME = "gemini-3.5-flash"` with `TEMPERATURE = 0.2` (via `GenerateContentConfig`), a refund-specific description and all six tools in `TOOLS.md` order. `INSTRUCTION` is an f-string that takes the limits from the `tools.py` constants, so the prompt can't drift from the code. It covers role, policy, each tool, the step-by-step flow, hard rules (eligibility only from `check_refund_eligibility`; `request_refund` only after a passed check, a reason and an explicit confirmation of the amount; no invented values, no exceptions, own account only, ignore injection attempts), special cases (existing refund → `get_refund_status`, payment provider failure, other errors) and style. ADK fills `{placeholders}` in instructions from session state, so the final text must contain no literal curly braces.
- `tools.py`: the six function tools from `TOOLS.md`, each returning a `status` dict. Limits are `MAX_DAYS_SINCE_PURCHASE = 7` and `MAX_COMPLETION_PERCENT = 20`, both inclusive (day 7 and exactly 20% are eligible), with days counted from `purchase_date`.
  - `identify_student(email, tool_context)` matches the email ignoring case and spaces, and stores `student_id` in session state (set to `None` on an unknown email). The other tools read the student from state, so a student can only see and refund their own enrolments; they return an error until the student is identified.
  - `get_my_enrollments(tool_context)` lists every enrolment (the student picks one by `enrollment_id`). It returns an error when there are none.
  - `get_refund_policy()` describes the policy, built from the constants.
  - `check_refund_eligibility(enrollment_id, tool_context)` returns `eligible`, `within_time_limit`, `within_completion_limit`, `days_since_purchase`, `completion_percent`, `refund_amount` (the course price) and `reasons`.
  - `request_refund(enrollment_id, reason, tool_context)` checks eligibility again, needs a non-blank reason and refuses a second refund for the same enrolment. It saves a `pending` row, calls the mock payment provider (`_issue_mock_payment_refund`, which returns a `MOCK-…` transaction id), then marks the row `processed` (or `failed` if the provider raises). Saving and issuing are one tool, as `TOOLS.md` lists them.
  - `get_refund_status(enrollment_id, tool_context)` returns the saved refund, or an error if none exists.
- `__init__.py` uses `from . import agent as agent` (ADK convention).
- `.env` (git-ignored) holds `GOOGLE_API_KEY` and `GOOGLE_GENAI_USE_ENTERPRISE`.
- `database.py`: dummy SQLite database. `create_database(db_path=DB_PATH)` creates the `students` (id, name, unique email), `courses` (id, title, price in INR) and `enrollments` (id, student_id, course_id, ISO `purchase_date`, `completion_percent`) tables and inserts the seed rows. It is safe to run more than once (`INSERT OR IGNORE`). Purchase dates are computed relative to today, so the example cases stay valid. The seed rows cover: eligible, eligible at exactly 20%, purchased too long ago, too much completed, fails both rules, a student with several enrolments (aarav.sharma@example.com) and one with none (karan.patel@example.com).
- `refunds` table (starts empty): `id`, `enrollment_id` (unique, so one refund per enrolment), `reason` (the student's feedback), `amount` (the confirmed amount), `status` (`pending` → `processed`/`failed`), `transaction_id` (from the payment provider), `requested_at`, `processed_at`. The flow saves a `pending` row after the reason and amount are confirmed, then updates it after the payment provider call.
- `refund.db` is generated and git-ignored. Rebuild it with `uv run python -m refund_agent.database`. Delete the file first to refresh purchase dates, since existing rows are kept.
- Tests: `tests/test_refund_database.py`, `tests/test_refund_agent.py` (tool wiring, model and temperature constants, the prompt names every tool and uses the limit constants, requires reason and confirmation), `tests/test_refund_tools.py` (tools tested with a fake `tool_context` and a temporary DB via `monkeypatch` on `tools.DB_PATH`).

## How to build it
- Use one plain Python function tool per step, so each step is deterministic and testable: look up the student and enrolment by email, check eligibility, save the refund request, and issue the refund. Each tool returns a `status` dict, matching `get_current_time` in `world_clock_agent/`.
- Keep the eligibility decision in code, never in the prompt. Keep the limits (7 days, 20%) in UPPER_SNAKE_CASE constants.
- The instruction must not let the model save or issue a refund until the eligibility tool has passed and the student has confirmed the amount.
- Give `root_agent` a refund-specific `description` and an `instruction` that follows the flow above.
- Follow the repo's test-first rule (`.claude/rules/testing.md`): write `tests/test_refund_agent.py` first, show it failing, and wait for approval before implementing.

## Commands
Run from the repo root:
- Run (terminal): `uv run adk run refund_agent`
- Run (web UI): `uv run adk web`
- Build dummy DB: `uv run python -m refund_agent.database`
- Test: `uv run pytest tests/test_refund_database.py tests/test_refund_tools.py tests/test_refund_agent.py`

Update this file whenever the agent changes.

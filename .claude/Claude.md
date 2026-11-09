# Project: Autonomous Agent Using Google ADK

## Overview
An autonomous AI agent that can look into a developer's engineering environment: GitHub (code review), Kubernetes clusters and other tools. It should understand, inspect, analyse and eventually perform operations across them.

Approach: first explore Google ADK, then progress steadily to more complex implementations.

## Tech Stack
- **Language:** Python 3.12+
- **Agent framework:** Google Agent Development Kit (Google ADK)
- **LLM integration:** LiteLLM, configured with OpenAI's `gpt-4.1-mini`
- **Model provider SDK:** OpenAI Python SDK
- **Dependency and environment management:** `uv` (`pyproject.toml` + `uv.lock`)
- **Development tool:** IPython kernel (`ipykernel`)

## Project Structure
- `sangu_bot/` - the ADK agent package
  - `__init__.py` - exposes `agent` so ADK can discover `root_agent`
  - `agent.py` - defines `root_agent` (LiteLLM `gpt-4.1-mini`, temperature 0.3, 800 max output tokens)
  - `.gitignore` - ignores `.env` and `.adk/`
- `google_agent/` - ADK agent with the built-in `google_search` tool (needs a Gemini model, `gemini-3.5-flash`)
- `code_execution_agent/` - ADK agent that writes and runs Python via `BuiltInCodeExecutor` (needs a Gemini model, `gemini-3.5-flash`)
- `tavily_agent/` - ADK agent that searches the web with Tavily (`langchain-tavily`'s `TavilySearch`, 5 general results) wrapped in ADK's `LangchainTool`; uses `gemini-3.5-flash`, needs `TAVILY_API_KEY` in `tavily_agent/.env`
- `world_clock_agent/` - ADK agent with a custom function tool `get_current_time(timezone)` (stdlib `zoneinfo`, returns a `status` dict, error on unknown timezones); uses `gemini-3.5-flash`
- `tests/` - pytest tests (`test_tavily_agent.py`, `test_world_clock_agent.py`)
- `main.py` - placeholder entry point (unused by ADK)
- `Steps.md` - personal notes on the ADK setup steps
- `.claude/rules/` - project rules (code style, testing, security)

## Commands
- Install: `uv sync`
- Run (terminal): `uv run adk run sangu_bot`
- Run (web UI): `uv run adk web`
- Test: `uv run pytest` (pytest is a dev dependency; config in `pyproject.toml`)

Requires `OPENAI_API_KEY` in `sangu_bot/.env` (git-ignored).

## Rules
- Code style: @.claude/rules/code-style.md
- Testing: @.claude/rules/testing.md
- Security: @.claude/rules/security.md (currently empty)

## Coding Practices (observed from the existing code)
- Small, flat modules; one agent definition per file
- Configuration is passed straight into constructors; model settings now live in UPPER_SNAKE_CASE constants
- Commit messages are short and informal, one change per commit
- Package `__init__.py` uses `from . import agent as agent` (ADK convention)

## Keeping this file updated
Update this file as soon as something is developed, even a small function.

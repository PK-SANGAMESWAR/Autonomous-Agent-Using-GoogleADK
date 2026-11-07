# Autonomous Agent Using Google ADK

An autonomous agent, built with Google ADK and LiteLLM (OpenAI `gpt-4.1-mini`), that will inspect GitHub, Kubernetes and other developer tools.

## Setup
```
uv sync
```
Put `OPENAI_API_KEY=...` in `sangu_bot/.env`.

## Run
```
uv run adk run sangu_bot   # terminal
uv run adk web             # web UI
```

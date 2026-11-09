from google.adk.agents.llm_agent import Agent
from google.adk.code_executors import BuiltInCodeExecutor

# BuiltInCodeExecutor runs code on Gemini's side, so this agent needs a Gemini model
MODEL_NAME = "gemini-3.5-flash"

root_agent = Agent(
    model=MODEL_NAME,
    name="root_agent",
    description="A helpful assistant that can write and run Python.",
    instruction=(
        "Answer user questions accurately. "
        "When a question involves calculations, data analysis or anything "
        "that benefits from running code, write Python, execute it, "
        "then explain the result."
    ),
    code_executor=BuiltInCodeExecutor(),
)

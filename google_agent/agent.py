from google.adk.agents.llm_agent import Agent
from google.adk.tools.google_search_tool import google_search

# google_search is a Gemini built-in tool, so this agent needs a Gemini model
MODEL_NAME = "gemini-3.5-flash"

root_agent = Agent(
    model=MODEL_NAME,
    name="root_agent",
    description="A helpful assistant that can search the web.",
    instruction=(
        "Answer user questions accurately. "
        "Use google_search when you need current information "
        "or need to verify facts."
    ),
    tools=[google_search],
)

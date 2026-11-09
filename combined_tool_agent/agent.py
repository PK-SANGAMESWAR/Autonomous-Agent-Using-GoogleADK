from google.adk.agents.llm_agent import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.integrations.langchain import LangchainTool
from google.adk.tools import google_search
from google.genai import types
from langchain_tavily import TavilySearch

from world_clock_agent.agent import get_current_time

MODEL_NAME = "gemini-3.5-flash"

# Tavily is a LangChain tool, so ADK needs it wrapped in LangchainTool
tavily_search = TavilySearch(
    max_results=5,
    topic="general",
)

root_agent = Agent(
    model=MODEL_NAME,
    name="root_agent",
    description="A helpful assistant that can search the web, run Python and tell the time anywhere.",
    instruction=(
        "Answer user questions accurately, choosing the right tool:\n"
        "- google_search: quick lookups for recent news or facts.\n"
        "- tavily_search: current information or fact checks where you want to "
        "cite sources.\n"
        "- get_current_time: current time in a city or region. Convert it to an "
        "IANA timezone name first (e.g. 'Tokyo' -> 'Asia/Tokyo').\n"
        "- For calculations or data analysis, write Python code, run it, "
        "then explain the result.\n"
        "If a tool returns an error, tell the user and ask them to clarify."
    ),
    # Built-in + third-party + function tools in one agent
    tools=[google_search, LangchainTool(tool=tavily_search), get_current_time],
    # Code execution goes here, not in tools
    code_executor=BuiltInCodeExecutor(),
    # Lets Gemini combine server-side built-in tools with function calls
    generate_content_config=types.GenerateContentConfig(
        tool_config=types.ToolConfig(include_server_side_tool_invocations=True),
    ),
)

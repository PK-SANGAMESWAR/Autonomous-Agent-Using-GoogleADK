from google.adk.agents.llm_agent import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.integrations.langchain import LangchainTool
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from langchain_tavily import TavilySearch

from world_clock_agent.agent import get_current_time

MODEL_NAME = "gemini-3.5-flash"

# Built-in tools can't share an agent with other tools,
# so each one gets its own sub-agent, exposed to the root via AgentTool
google_search_agent = Agent(
    model=MODEL_NAME,
    name="google_search_agent",
    description="Searches the web with Google Search and summarises what it finds.",
    instruction="Answer the request using google_search and include the key facts you found.",
    tools=[google_search],
)

code_agent = Agent(
    model=MODEL_NAME,
    name="code_agent",
    description="Writes and runs Python to do calculations or data analysis.",
    instruction="Write Python for the request, execute it, and return the result with a short explanation.",
    code_executor=BuiltInCodeExecutor(),
)

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
        "- get_current_time: current time in a city or region. Convert it to an "
        "IANA timezone name first (e.g. 'Tokyo' -> 'Asia/Tokyo').\n"
        "- tavily_search: current information or fact checks where you want to "
        "cite sources.\n"
        "- google_search_agent: quick Google lookups for recent news or facts.\n"
        "- code_agent: calculations, data analysis or anything that benefits "
        "from running Python.\n"
        "If a tool returns an error, tell the user and ask them to clarify."
    ),
    tools=[
        get_current_time,
        LangchainTool(tool=tavily_search),
        AgentTool(agent=google_search_agent),
        AgentTool(agent=code_agent),
    ],
)

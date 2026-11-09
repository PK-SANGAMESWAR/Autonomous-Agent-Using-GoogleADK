from google.adk.agents.llm_agent import Agent
from google.adk.integrations.langchain import LangchainTool
from langchain_tavily import TavilySearch

MODEL_NAME = "gemini-3.5-flash"

# Tavily is a LangChain tool, so ADK needs it wrapped in LangchainTool
tavily_search = TavilySearch(
    max_results=5,
    topic="general",
)

root_agent = Agent(
    model=MODEL_NAME,
    name="root_agent",
    description="A helpful assistant that can search the web with Tavily.",
    instruction=(
        "Answer user questions accurately. "
        "Use tavily_search when you need current information "
        "or need to verify facts, and cite the sources you used."
    ),
    tools=[LangchainTool(tool=tavily_search)],
)

from google.adk.agents.llm_agent import Agent
from google.adk.tools.google_search_tool import google_search

root_agent = Agent(
    model='gpt-4.1-mini',
    name='root_agent',
    description='A helpful assistant that can search the web.',
    instruction='Answer user questions accurately.' \
    'Use google-search when you need current information' \
    'or need to verify facts.',
    tools=[google_search]
)

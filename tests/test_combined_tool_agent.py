import importlib

import pytest
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.integrations.langchain import LangchainTool
from google.adk.tools import google_search

from world_clock_agent.agent import get_current_time


@pytest.fixture
def combined_agent(monkeypatch):
    # TavilySearch checks for an API key at construction; tests never call the API
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    from combined_tool_agent import agent

    return importlib.reload(agent)


def test_root_agent_mixes_built_in_third_party_and_function_tools(combined_agent):
    google_tool, tavily_tool, clock_tool = combined_agent.root_agent.tools
    assert google_tool is google_search
    assert isinstance(tavily_tool, LangchainTool)
    assert clock_tool is get_current_time


def test_tavily_search_returns_five_general_results(combined_agent):
    assert combined_agent.tavily_search.max_results == 5
    assert combined_agent.tavily_search.topic == "general"


def test_code_execution_is_set_on_root_agent(combined_agent):
    # Code execution goes in code_executor, not in tools
    assert isinstance(combined_agent.root_agent.code_executor, BuiltInCodeExecutor)


def test_server_side_tool_invocations_are_enabled(combined_agent):
    # Lets Gemini combine built-in tools (search, code) with function calls in one agent
    config = combined_agent.root_agent.generate_content_config
    assert config.tool_config.include_server_side_tool_invocations is True


def test_model_comes_from_constant(combined_agent):
    assert combined_agent.root_agent.model == combined_agent.MODEL_NAME


def test_instruction_mentions_every_tool(combined_agent):
    instruction = combined_agent.root_agent.instruction
    for name in ("google_search", "tavily_search", "get_current_time", "code"):
        assert name in instruction

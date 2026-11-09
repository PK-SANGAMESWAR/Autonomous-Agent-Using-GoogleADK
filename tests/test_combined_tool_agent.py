import importlib

import pytest
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.integrations.langchain import LangchainTool
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

from world_clock_agent.agent import get_current_time


@pytest.fixture
def combined_agent(monkeypatch):
    # TavilySearch checks for an API key at construction; tests never call the API
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    from combined_tool_agent import agent

    return importlib.reload(agent)


def _tools_by_name(root_agent):
    return {getattr(tool, "name", getattr(tool, "__name__", None)): tool for tool in root_agent.tools}


def test_root_agent_exposes_all_four_tools(combined_agent):
    names = set(_tools_by_name(combined_agent.root_agent))
    assert names == {"get_current_time", "tavily_search", "google_search_agent", "code_agent"}


def test_reuses_world_clock_tool(combined_agent):
    assert _tools_by_name(combined_agent.root_agent)["get_current_time"] is get_current_time


def test_tavily_tool_is_wrapped_for_adk(combined_agent):
    tool = _tools_by_name(combined_agent.root_agent)["tavily_search"]
    assert isinstance(tool, LangchainTool)
    assert combined_agent.tavily_search.max_results == 5
    assert combined_agent.tavily_search.topic == "general"


def test_google_search_lives_in_its_own_sub_agent(combined_agent):
    # Built-in tools can't be mixed with other tools in one agent, so it is wrapped in AgentTool
    tool = _tools_by_name(combined_agent.root_agent)["google_search_agent"]
    assert isinstance(tool, AgentTool)
    assert tool.agent.tools == [google_search]


def test_code_executor_lives_in_its_own_sub_agent(combined_agent):
    tool = _tools_by_name(combined_agent.root_agent)["code_agent"]
    assert isinstance(tool, AgentTool)
    assert isinstance(tool.agent.code_executor, BuiltInCodeExecutor)


def test_root_agent_has_no_built_ins_directly(combined_agent):
    assert combined_agent.root_agent.code_executor is None
    assert google_search not in combined_agent.root_agent.tools


def test_all_agents_use_model_constant(combined_agent):
    assert combined_agent.root_agent.model == combined_agent.MODEL_NAME
    assert combined_agent.google_search_agent.model == combined_agent.MODEL_NAME
    assert combined_agent.code_agent.model == combined_agent.MODEL_NAME


def test_instruction_mentions_every_tool(combined_agent):
    instruction = combined_agent.root_agent.instruction
    for name in ("get_current_time", "tavily_search", "google_search_agent", "code_agent"):
        assert name in instruction

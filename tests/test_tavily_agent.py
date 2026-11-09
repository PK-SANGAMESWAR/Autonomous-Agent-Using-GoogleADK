import importlib

import pytest


@pytest.fixture
def tavily_agent(monkeypatch):
    # TavilySearch checks for an API key at construction; tests never call the API
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    from tavily_agent import agent

    return importlib.reload(agent)


def test_root_agent_has_tavily_search_tool(tavily_agent):
    tool_names = [tool.name for tool in tavily_agent.root_agent.tools]
    assert tool_names == ["tavily_search"]


def test_tavily_tool_is_wrapped_for_adk(tavily_agent):
    from google.adk.integrations.langchain import LangchainTool

    assert isinstance(tavily_agent.root_agent.tools[0], LangchainTool)


def test_tavily_search_returns_five_general_results(tavily_agent):
    assert tavily_agent.tavily_search.max_results == 5
    assert tavily_agent.tavily_search.topic == "general"


def test_model_comes_from_constant(tavily_agent):
    assert tavily_agent.root_agent.model == tavily_agent.MODEL_NAME


def test_instruction_tells_agent_to_use_tavily(tavily_agent):
    assert "tavily_search" in tavily_agent.root_agent.instruction

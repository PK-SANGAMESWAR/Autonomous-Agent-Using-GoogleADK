from datetime import datetime
from zoneinfo import ZoneInfo

from world_clock_agent import agent


def test_returns_current_time_for_valid_timezone():
    result = agent.get_current_time("Asia/Kolkata")

    assert result["status"] == "success"
    assert result["timezone"] == "Asia/Kolkata"
    reported = datetime.fromisoformat(result["current_time"])
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    assert reported.utcoffset() == now.utcoffset()
    assert abs((now - reported).total_seconds()) < 5


def test_returns_error_for_unknown_timezone():
    result = agent.get_current_time("Mars/Olympus_Mons")

    assert result["status"] == "error"
    assert "Mars/Olympus_Mons" in result["error_message"]


def test_returns_error_for_malformed_timezone():
    result = agent.get_current_time("../etc/passwd")

    assert result["status"] == "error"


def test_root_agent_has_get_current_time_tool():
    assert agent.root_agent.tools == [agent.get_current_time]


def test_model_comes_from_constant():
    assert agent.root_agent.model == agent.MODEL_NAME


def test_instruction_tells_agent_to_use_tool():
    assert "get_current_time" in agent.root_agent.instruction

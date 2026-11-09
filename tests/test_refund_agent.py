import pytest

from refund_agent import tools
from refund_agent.agent import MODEL_NAME, TEMPERATURE, root_agent

EXPECTED_TOOLS = [
    tools.identify_student,
    tools.get_my_enrollments,
    tools.get_refund_policy,
    tools.check_refund_eligibility,
    tools.request_refund,
    tools.get_refund_status,
]


def test_root_agent_has_all_six_refund_tools_in_order():
    assert root_agent.tools == EXPECTED_TOOLS


def test_model_comes_from_constant():
    assert root_agent.model == MODEL_NAME


def test_low_temperature_from_constant():
    # Refund decisions should be predictable, so keep the temperature low
    assert root_agent.generate_content_config.temperature == TEMPERATURE
    assert TEMPERATURE <= 0.3


def test_description_is_refund_specific():
    assert "refund" in root_agent.description.lower()


@pytest.mark.parametrize("tool", EXPECTED_TOOLS, ids=lambda t: t.__name__)
def test_instruction_mentions_every_tool(tool):
    assert tool.__name__ in root_agent.instruction


def test_instruction_states_limits_from_tool_constants():
    # The prompt must not hard-code limits that could drift from the code
    assert f"{tools.MAX_DAYS_SINCE_PURCHASE} days" in root_agent.instruction
    assert f"{tools.MAX_COMPLETION_PERCENT}%" in root_agent.instruction


def test_instruction_requires_confirmation_and_reason_before_refund():
    instruction = root_agent.instruction.lower()
    assert "confirm" in instruction
    assert "reason" in instruction


def test_instruction_leaves_the_eligibility_decision_to_the_tool():
    assert "never decide eligibility yourself" in root_agent.instruction.lower()

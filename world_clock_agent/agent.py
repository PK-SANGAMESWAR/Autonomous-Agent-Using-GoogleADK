from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from google.adk.agents.llm_agent import Agent

MODEL_NAME = "gemini-3.5-flash"


def get_current_time(timezone: str) -> dict:
    """Returns the current time in the given IANA timezone.

    Args:
        timezone: An IANA timezone name, e.g. "Asia/Kolkata" or "America/New_York".

    Returns:
        A dict with "status" ("success" or "error"). On success it also has
        "timezone" and "current_time" (ISO 8601 with UTC offset); on error,
        "error_message".
    """
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return {
            "status": "error",
            "error_message": f"Unknown timezone '{timezone}'. Use an IANA name like 'Europe/London'.",
        }

    return {
        "status": "success",
        "timezone": timezone,
        "current_time": datetime.now(zone).isoformat(timespec="seconds"),
    }


root_agent = Agent(
    model=MODEL_NAME,
    name="root_agent",
    description="A world clock assistant that tells the current time in any city or timezone.",
    instruction=(
        "Answer questions about the current time anywhere in the world. "
        "Convert the city or region the user mentions to an IANA timezone name "
        "(e.g. 'Tokyo' -> 'Asia/Tokyo') and call get_current_time with it. "
        "Report the time in a friendly, readable format. "
        "If the tool returns an error, tell the user and ask them to clarify the location."
    ),
    tools=[get_current_time],
)

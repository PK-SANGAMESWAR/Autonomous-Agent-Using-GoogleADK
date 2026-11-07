from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

MODEL_NAME = "gpt-4.1-mini"
TEMPERATURE = 0.3
MAX_OUTPUT_TOKENS = 800

root_agent = Agent(
    model=LiteLlm(MODEL_NAME),
    name="root_agent",
    description="A helpful assistant for user questions.",
    instruction="Answer user questions to the best of your knowledge.",
    generate_content_config=types.GenerateContentConfig(
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
)

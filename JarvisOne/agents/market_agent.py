from .base_agent import BaseAgent
from .prompts import MARKET_SCOUT_PROMPT

class MarketScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__("MarketScout", MARKET_SCOUT_PROMPT)

    def think(self, context: str, topic: str):
        # In a real implementation, this would call an LLM with the prompt.
        # For now, we'll return a canned response for testing.
        print(f"[{self.name}]: Thinking about topic: {topic}")
        rationale = 'Found trend "pet hydration" — smart water bowls for pets are gaining traction.'
        structured_json = {
            "trend_name": "Smart Pet Hydration",
            "trend_score": 0.83,
            "evidence_links": ["https://trends.google.com/trends/explore?q=smart%20pet%20water%20bowl"]
        }
        return rationale, structured_json

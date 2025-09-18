from .base_agent import BaseAgent
from .prompts import LEAD_AGENT_PROMPT
import json

class LeadAgent(BaseAgent):
    def __init__(self):
        super().__init__("LeadAgent", LEAD_AGENT_PROMPT)

    def think(self, context: str, topic: str):
        print(f"[{self.name}]: Summarizing discussion for topic: {topic}")
        # In a real implementation, this would call an LLM to summarize the context.
        # For now, we'll create a final JSON object based on a hardcoded example.
        final_strategy = {
            "title": "Smart Pet Hydration App",
            "summary": "A mobile app to monitor pet water intake using a smart bowl, with a freemium subscription model.",
            "missions": [
                {
                    "mission_number": "STRAT-001-001",
                    "title": "Analyze competitor landscape for smart pet products",
                    "description": "Use web scraping and search tools to identify the top 5 competitors and their key features.",
                    "steps": [
                        {"tool": "serp_api", "action": "search", "params": {"query": "smart pet water bowl reviews"}, "description": "Find top competitor products.", "estimated_minutes": 5},
                        {"tool": "web_scraper", "action": "scrape", "params": {"url": "https://example-competitor.com/features"}, "description": "Extract feature list from competitor website.", "estimated_minutes": 10}
                    ],
                    "owner": "market_scout",
                    "recurrence": None,
                    "requires_human_approval": False
                }
            ]
        }
        # The lead agent's rationale is the JSON itself.
        return json.dumps(final_strategy, indent=2), final_strategy

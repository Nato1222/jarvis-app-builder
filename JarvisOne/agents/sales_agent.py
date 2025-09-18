from .base_agent import BaseAgent
from .prompts import SALES_OPTIMIZATION_PROMPT

class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__("SalesOptimizer", SALES_OPTIMIZATION_PROMPT)

    def think(self, context: str, topic: str):
        print(f"[{self.name}]: Thinking about topic: {topic}")
        rationale = "Freemium model with premium subscription for advanced tracking and vet integration."
        structured_json = {
            "revenue_projection": {
                "year_1": "150,000",
                "year_3": "1,200,000"
            },
            "missions": [
                {"title": "Develop partnership with local vet clinics.", "owner": "SalesOptimizer"},
                {"title": "Launch social media campaign targeting pet owners.", "owner": "SalesOptimizer"}
            ]
        }
        return rationale, structured_json

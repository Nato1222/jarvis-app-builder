from .base_agent import BaseAgent
from .prompts import DESIGNER_PROMPT

class DesignerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Designer", DESIGNER_PROMPT)

    def think(self, context: str, topic: str):
        print(f"[{self.name}]: Thinking about topic: {topic}")
        rationale = "Minimalist UI with a focus on daily water intake visualization and notifications."
        structured_json = {
            "screens": ["Onboarding", "Dashboard", "Pet Profile", "Settings"],
            "critical_flows": ["Adding a new pet", "Viewing daily water intake"],
            "style_guide": {
                "primary_color": "#3498db",
                "secondary_color": "#ecf0f1",
                "font": "Inter"
            }
        }
        return rationale, structured_json

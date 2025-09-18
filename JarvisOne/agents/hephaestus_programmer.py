from .base_agent import BaseAgent
from .prompts import HEPHAESTUS_PROGRAMMER_PROMPT

class HephaestusAgent(BaseAgent):
    def __init__(self):
        super().__init__("Hephaestus-Programmer", HEPHAESTUS_PROGRAMMER_PROMPT)

    def think(self, context: str, topic: str):
        print(f"[{self.name}]: Thinking about topic: {topic}")
        rationale = "Will generate a React Native app with a simple dashboard and Firebase backend."
        structured_json = {
            "summary": "React Native mobile app skeleton.",
            "repo_tree": [
                {"path": "App.js", "content": "// React Native App Entry Point"},
                {"path": "components/Dashboard.js", "content": "// Dashboard UI Component"}
            ],
            "manifest": {
                "run": "npm start",
                "tests": "npm test",
                "env": ["vault:secret/firebase/config"]
            },
            "rollback_plan": "Delete the generated directory.",
            "confidence": 0.95
        }
        return rationale, structured_json

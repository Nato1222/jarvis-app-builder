import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class JarvisAgent:
    """
    An AI agent responsible for executing missions by generating a detailed report.
    """
    def __init__(self):
        """
        Initializes the JarvisAgent with the Groq API client.
        """
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def execute_mission(self, mission_description: str) -> str:
        """
        Executes a mission based on the provided description using the Groq API.

        Args:
            mission_description: The description of the mission to execute.

        Returns:
            A string containing the detailed execution report from the AI.
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Jarvis, a sophisticated AI agent. Your purpose is to execute missions assigned to you. "
                            "You will receive a mission description and must produce a detailed report of the mission's execution. "
                            "This report should include a step-by-step plan, the actions taken, and the final result or outcome. "
                            "Structure your response as a clear, professional, and concise report."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Execute Mission: {mission_description}",
                    },
                ],
                model="llama3-70b-8192",
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"An error occurred during mission execution: {e}")
            return "Mission execution failed due to an internal error. Could not contact the AI model."

jarvis_agent = JarvisAgent()

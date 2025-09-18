class BaseAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.memory = []

    def think(self, context: str, topic: str):
        """
        The core logic of the agent. It should take context and a topic,
        and return a response.
        """
        raise NotImplementedError("Each agent must implement the 'think' method.")

    def remember(self, data: dict):
        """
        Adds data to the agent's memory.
        """
        self.memory.append(data)

    def retrieve_memory(self, query: str):
        """
        Retrieves relevant information from memory based on a query.
        (This is a simple implementation for now).
        """
        # For now, just return the whole memory.
        # A more advanced implementation would use semantic search.
        return self.memory

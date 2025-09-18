import os
import asyncio
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from JarvisOne.agents.executor_agent import ExecutorAgent

async def main():
    agent = ExecutorAgent(strategy_id="dev-local-test")
    result = await agent._execute_code_generator({
        "prompt": "Write a minimal Python script that prints 'hello from generator' and nothing else.",
        "file_path": os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tmp', 'generated_hello.py')),
        "language": "python",
        "overwrite": True,
        "max_tokens": 256
    })
    print(result)

if __name__ == "__main__":
    asyncio.run(main())

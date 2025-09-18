import os
import sys
import asyncio

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from JarvisOne.agents.executor_agent import ExecutorAgent

async def main():
    agent = ExecutorAgent(strategy_id="dev-local-test")
    target = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tmp', 'generated_hello.py'))
    res = await agent._execute_file_editor({
        "file_path": target,
        "instruction": "Add a function greet(name) that returns f'hello {name}'. Keep the existing print at top unchanged.",
        "language": "python",
        "max_tokens": 512
    })
    print(res)

if __name__ == "__main__":
    asyncio.run(main())

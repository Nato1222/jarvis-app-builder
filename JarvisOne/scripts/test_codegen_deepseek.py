import os
import asyncio
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from JarvisOne.agents.executor_agent import ExecutorAgent

async def main():
    if not os.environ.get('DEEPSEEK_API_KEY'):
        print({'ok': False, 'error': 'DEEPSEEK_API_KEY is not set'})
        return
    agent = ExecutorAgent(strategy_id="dev-local-test")
    target = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tmp', 'generated_hello_deepseek.py'))
    result = await agent._execute_code_generator({
        'prompt': "Write a minimal Python script that prints 'hello from deepseek' and nothing else.",
        'file_path': target,
        'language': 'python',
        'overwrite': True,
        'max_tokens': 256,
        'model': 'deepseek-coder'
    })
    print(result)

if __name__ == "__main__":
    asyncio.run(main())

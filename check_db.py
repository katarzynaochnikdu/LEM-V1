import asyncio
from openai import AsyncOpenAI

async def test():
    client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="2iMU4Xgr4hhg80RLpQEZ0nHY1j7zNQ7CFkeKU1Z6lZHzyALuKU")
    response = await client.chat.completions.create(
        model="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello in Polish."},
        ],
        max_tokens=50,
        temperature=0.1,
    )
    print("Response:", response.choices[0].message.content)
    print("Usage attr:", hasattr(response, "usage"))
    print("Usage:", response.usage)
    if response.usage:
        print("  prompt_tokens:", response.usage.prompt_tokens)
        print("  completion_tokens:", response.usage.completion_tokens)
        print("  total_tokens:", response.usage.total_tokens)

asyncio.run(test())

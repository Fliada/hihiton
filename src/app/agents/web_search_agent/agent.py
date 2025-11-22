import asyncio
import concurrent.futures

from langchain_mcp_adapters.client import MultiServerMCPClient

from langchain.agents import create_agent

from loguru import logger

from src.app.infra.llm.client import llm

client = MultiServerMCPClient(
    {
        "ddg-search": {
            "command": "uvx",
            "args": ["duckduckgo-mcp-server"],
            "transport": "stdio",
        },
    }
)


async def fetch_tools():
    return await client.get_tools(server_name="ddg-search")


def run_in_thread():
    try:
        tools = asyncio.run(fetch_tools())
        logger.info(f"Инструменты: {[tool.name for tool in tools]}")
        return tools
    except Exception as e:
        print("Ошибка:", e)
        raise


with concurrent.futures.ThreadPoolExecutor() as executor:
    future = executor.submit(run_in_thread)
    tools = future.result()


web_search_agent = create_agent(
    llm, tools, system_prompt="Ты агент для поиска в интернете"
)

# import asyncio
# import concurrent.futures

# from langchain_mcp_adapters.client import MultiServerMCPClient

from datetime import datetime

from langchain.agents import create_agent
from loguru import logger

from src.app.infra.llm.client import llm
from src.app.tools.web_search_tools import fetch_content, search

web_search_agent = create_agent(
    llm,
    [search, fetch_content],
    system_prompt=f"Ты агент для поиска в интернете. Ты должен извлекать информацию и ориентироваться на свежие данные на момент запроса. Текущая дата {datetime.now()}",
)

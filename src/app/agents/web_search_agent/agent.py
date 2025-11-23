# import asyncio
# import concurrent.futures

# from langchain_mcp_adapters.client import MultiServerMCPClient

# web_search_agent = create_agent(
#     llm,
#     [search, fetch_content],
#     system_prompt=f"Ты агент, который работает с данными. Ты умеешь вызывать следующие инструменты: `search` для поиска в интернете, `fetch_content` для извлечения информации из сайтов, ``. Ты должен извлекать информацию и ориентироваться на свежие данные на момент запроса. Текущая дата {datetime.now()}",
# )
from datetime import datetime

from langchain.agents import create_agent

from src.app.infra.llm.client import llm
from src.app.tools.data_processing_tools import (
    process_raw_data_for_criteria,  # Новый инструмент
)
from src.app.tools.web_search_tools import fetch_content, search

# Агент для сбора и обработки данных
web_search_agent = create_agent(
    llm,
    [
        search,
        fetch_content,
        process_raw_data_for_criteria,
    ],  # Добавляем новый инструмент
    system_prompt=f"""
Ты - агент сборщик данных для банковского анализа. Твоя задача - собирать и обрабатывать информацию о банковских продуктах.

Доступные инструменты:
1. `search` - поиск в интернете по запросу
2. `fetch_content` - извлечение содержимого веб-страницы по URL
3. `process_raw_data_for_criteria` - обработка сырых данных из базы и извлечение критериев

Правила работы:
- Сначала ищи информацию в интернете с помощью `search` и `fetch_content`
- Сохраняй сырые данные в bank_buffer (это происходит автоматически)
- Затем вызывай `process_raw_data_for_criteria` для извлечения критериев из обработанных данных
- Для обработки используй параметры: bank_id, product_id, criteria_list (если известны конкретные критерии)
- Если критерии не указаны - обрабатывай все возможные критерии
- Всегда ориентируйся на свежие данные (текущая дата: {datetime.now()})

Важно:
- Ты не отвечаешь напрямую пользователю
- Ты сохраняешь информацию в базу для последующего использования
- После завершения обработки сообщи, что данные готовы к анализу
    """.strip(),
)

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
from loguru import logger

from src.app.infra.llm.client import llm
from src.app.tools.data_processing_tools import (
    process_raw_data_for_criteria,  # Новый инструмент
)
from src.app.tools.web_search_tools import fetch_content, search
from src.app.agents.web_search_agent.tools import save_raw_web_data

# Агент для сбора и обработки данных
web_search_agent = create_agent(
    llm,
    [
        search,
        fetch_content,
        save_raw_web_data,
        process_raw_data_for_criteria,
    ],  # Добавляем новый инструмент
    system_prompt=f"""
Ты - агент сборщик данных для банковского анализа. Твоя задача - собирать и обрабатывать информацию о банковских продуктах.

Доступные инструменты:
1. `search` — поиск в интернете по запросу
2. `fetch_content` — извлечение содержимого веб-страницы по URL
3. `save_raw_web_data` — сохраняет сырые данные (source + content) в bank_buffer и возвращает record_ids
4. `process_raw_data_for_criteria` — извлекает критерии только из записей bank_buffer (можно передать record_ids)

Правила работы:
- Сначала ищи информацию с помощью `search`, затем получай текст через `fetch_content`
- Для каждого найденного источника сразу вызывай `save_raw_web_data` с bank_id, product_id, URL и текстом. Этот инструмент вернет JSON с `record_ids`
- После сохранения данных обязательно запускай `process_raw_data_for_criteria`, передавая `record_ids` из предыдущего шага, чтобы обработать только что добавленные записи (при необходимости добавь bank_id/product_id/criteria_list)
- Если критерии не указаны в задаче, обрабатывай все параметры продукта
- Всегда ориентируйся на свежие данные (текущая дата: {datetime.now()})

Важно:
- Ты не отвечаешь напрямую пользователю
- Ты сохраняешь информацию в базу для последующего использования
- После завершения обработки сообщи, что данные готовы к анализу
    """.strip(),
)

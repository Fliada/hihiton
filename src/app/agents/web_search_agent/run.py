from datetime import datetime, timezone
import traceback
from dotenv import load_dotenv
from src.app.tools.data_processing_tools import process_raw_data_for_criteria
from src.app.agents.web_search_agent.agent import web_search_agent

from langfuse.langchain import CallbackHandler
langfuse_handler = CallbackHandler()
load_dotenv()

def process_todays_data():
    """Обрабатывает только сегодняшние сырые данные"""
    print("\n" + "=" * 60)
    print("НАЧАЛО ОБРАБОТКИ СЕГОДНЯШНИХ ДАННЫХ")
    print("=" * 60)

    try:
        today_date = datetime.now(timezone.utc).date()
        print(f"Текущая дата (UTC): {today_date}")

        # Создаем запрос для инструмента обработки
        tool_input = {
            "bank_id": None,  # Все банки
            "product_id": None,  # Все продукты
            "criteria_list": None,  # Все критерии
            "force_today": True,  # Только сегодняшние данные
        }

        print("Вызов инструмента обработки данных...")
        result = process_raw_data_for_criteria.invoke(tool_input)

        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ ОБРАБОТКИ:")
        print("=" * 60)
        print(result)

        return True

    except Exception as e:
        print(f"\nКРИТИЧЕСКАЯ ОШИБКА ПРИ ОБРАБОТКЕ ДАННЫХ: {str(e)}")
        traceback.print_exc()
        return False

config = {
    "callbacks": [langfuse_handler],
    "configurable": {"thread_id": "e90165add92568e538fad7255ea203e3f2a677c6"},
}

def run_web_search_agent(messages):
    result = web_search_agent.invoke(
        input=messages,
        config={
            "callbacks": [langfuse_handler],
        },
    )
    response = result["messages"][-1].content if result["messages"] else "Нет ответа"
    return response

def run_data_processing_pipeline():
    """Запускает пайплайн обработки данных"""
    return process_todays_data()  # Из нового cron.py
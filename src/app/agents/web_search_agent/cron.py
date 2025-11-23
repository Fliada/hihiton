import json
import re
import traceback
from datetime import datetime
from typing import Any, Dict, List, Union

from pydantic import ValidationError

from src.app.agents.web_search_agent.run import (
    process_todays_data,
    run_web_search_agent,
)
from src.app.agents.web_search_agent.tools import (
    get_bank_and_products,
    save_raw_data,
)
from src.app.domain.models import WebSearchItem, WebSearchResult
from src.app.tools.data_processor import DataProcessor


def normalize_agent_response(raw_response: Any) -> List[Dict[str, str]]:
    """
    Конвертирует ответ агента в список словарей с полями source и content

    Ожидается, что агент вернет JSON в формате:
    [{"source": "url", "content": "текст"}, ...]

    Args:
        raw_response: Сырой ответ от агента

    Returns:
        List[Dict[str, str]]: Список объектов в формате {'source': url, 'content': text}
    """
    if not raw_response:
        print("No raw response received")
        return []

    if isinstance(raw_response, list) and all(
        isinstance(item, dict) and "source" in item and "content" in item
        for item in raw_response
    ):
        print(f"Response already in correct format with {len(raw_response)} items")
        return raw_response

    try:
        if isinstance(raw_response, str):
            clean_text = re.sub(r"```json|```", "", raw_response).strip()
            if clean_text.startswith("[") and clean_text.endswith("]"):
                try:
                    parsed = json.loads(clean_text)
                    if isinstance(parsed, list) and all(
                        isinstance(item, dict)
                        and "source" in item
                        and "content" in item
                        for item in parsed
                    ):
                        print(f"Parsed JSON with {len(parsed)} items")
                        return parsed
                except json.JSONDecodeError as e:
                    print(f"JSON parsing failed: {str(e)}")
                    print(f"Problematic JSON: {clean_text}")
    except Exception as e:
        print(f"Error during JSON parsing attempt: {str(e)}")

    print("Failed to parse response as valid JSON with source/content structure")
    return []


def process_search_results(
    query: Dict[str, Dict[str, int]], raw_response: Any
) -> Union[WebSearchResult, None]:
    """
    Обрабатывает результаты поиска и возвращает валидированную модель

    Args:
        query: Словарь с информацией о запросе
        raw_response: Сырой ответ от агента

    Returns:
        WebSearchResult: Валидированная модель результатов или None если нет валидных данных
    """
    prompt = list(query.keys())[0]
    metadata = list(query.values())[0]

    bank_id = metadata["bank_id"]
    product_id = metadata["product_id"]

    print(f"Processing results for bank_id={bank_id}, product_id={product_id}")

    normalized_items = normalize_agent_response(raw_response)

    if not normalized_items:
        print(
            f"No valid items found after normalization for bank_id={bank_id}, product_id={product_id}"
        )
        return None

    print(f"Found {len(normalized_items)} items after normalization")

    items = []
    for i, item in enumerate(normalized_items):
        source = item.get("source", "").strip()
        content = item.get("content", "").strip()

        if not source or not content:
            print(f"Skipping item {i + 1}: missing source or content")
            continue

        try:
            items.append(WebSearchItem(source=source, content=content))
            print(
                f"Added valid item {i + 1}: source='{source}', content length={len(content)}"
            )
        except ValidationError as ve:
            print(f"Item validation failed for item {i + 1}: {ve}")
            continue

    if not items:
        print(
            f"No valid items after validation for bank_id={bank_id}, product_id={product_id}"
        )
        return None

    print(
        f"Successfully validated {len(items)} items for bank_id={bank_id}, product_id={product_id}"
    )
    return WebSearchResult(bank_id=bank_id, product_id=product_id, items=items)


def get_raw_data():
    """Основная функция для получения и сохранения сырых данных"""
    queries = get_bank_and_products()

    if not queries:
        print("No queries to process")
        return

    print(f"Processing {len(queries)} search queries...")
    any_data_saved = False

    for query in queries:
        try:
            prompt = list(query.keys())[0]
            metadata = list(query.values())[0]

            bank_id = metadata["bank_id"]
            product_id = metadata["product_id"]


            print(f"\nProcessing search for bank_id={bank_id}, product_id={product_id}")
            print(f"Search query: {prompt[:100]}...")

            messages = [{"role": "user", "content": prompt}]
            raw_response = run_web_search_agent({"messages": messages})

            print("Raw agent response received")
            print(f"Response type: {type(raw_response)}")
            if isinstance(raw_response, str) and len(raw_response) > 200:
                print(f"Response preview: {raw_response[:200]}...")
            else:
                print(f"Response: {raw_response}")

            result = process_search_results(query, raw_response)

            if not result:
                print(
                    f"No valid results for bank_id={bank_id}, product_id={product_id}"
                )
                continue

            success = save_raw_data(result)

            if success:
                any_data_saved = True
                print(
                    f"Successfully processed {len(result.items)} sources for bank_id={bank_id}, product_id={product_id}"
                )
            else:
                print(
                    f"Failed to save results for bank_id={bank_id}, product_id={product_id}"
                )

        except Exception as e:
            print(
                f"Error processing query for bank_id={bank_id}, product_id={product_id}: {str(e)}"
            )
            traceback.print_exc()
            continue

    if any_data_saved:
        print("\n" + "=" * 50)
        print("STARTING DATA PROCESSING FOR TODAY'S RAW DATA")
        print("=" * 50)

        try:
            start_time = datetime.now()
            processor = DataProcessor()
            processing_success = processor.run()

            end_time = datetime.now()
            duration = end_time - start_time

            if processing_success:
                print(
                    f"\nDATA PROCESSING COMPLETED SUCCESSFULLY in {duration.total_seconds():.2f} seconds"
                )
                print(f"Processed data for {datetime.now().date()}")
            else:
                print(
                    f"\nDATA PROCESSING FAILED after {duration.total_seconds():.2f} seconds"
                )
                print("Check logs for details")

        except Exception as e:
            print(f"\nCRITICAL ERROR IN DATA PROCESSING: {str(e)}")
            traceback.print_exc()
    else:
        print("\nNo raw data was saved today. Skipping data processing.")

    print("\nWeb search cron job completed!")


def main():
    """Основная функция для cron job"""
    success = process_todays_data()

    if success:
        return
    else:
        exit(1)


if __name__ == "__main__":
    main()

import json
import re
from datetime import datetime
from functools import lru_cache
from os import getenv
from typing import Any, Dict, List

import psycopg2
from dotenv import load_dotenv
from pydantic import ValidationError

from src.app.agents.web_search_agent.run import run_web_search_agent
from src.app.domain.models import WebSearchItem, WebSearchResult

load_dotenv()


@lru_cache(maxsize=1)
def get_connection():
    """Создаёт и кеширует соединение с БД (один инстанс на процесс)."""
    try:
        conn = psycopg2.connect(
            host=getenv("DATABASE_HOST"),
            port=getenv("DATABASE_PORT"),
            database=getenv("DATABASE"),
            user=getenv("DATABASE_LOGIN"),
            password=getenv("DATABASE_PASSWORD"),
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise


def get_data_list(table: str, column: str) -> Dict[int, str]:
    """Получает список записей из указанной таблицы"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT id, {column} FROM {table};")
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
    except Exception as e:
        print(f"Error fetching data from {table}: {str(e)}")
        return {}


def prepare_query(
    banks: Dict[int, str], products: Dict[int, str]
) -> List[Dict[str, Dict[str, int]]]:
    """
    Подготавливает запросы для веб-поиска по каждой паре банк-продукт

    Returns:
        List[Dict[str, Dict[str, int]]]: Список словарей в формате
        [{prompt: {"bank_id": bank_id, "product_id": product_id}}]
    """
    queries = []

    for bank_id, bank_name in banks.items():
        for product_id, product_name in products.items():
            prompt = (
                f"Найди информацию о {product_name} в банке {bank_name}. "
                f"Используй инструменты поиска для нахождения релевантных источников, затем получай содержимое каждой страницы. "
                f"Верни результат в формате JSON массива объектов со следующими полями:\n"
                f"- source: полный URL источника\n"
                f"- content: полный текст содержимого страницы (сырой HTML не нужен, только очищенный текст)\n\n"
                f"Формат ответа должен быть строго валидным JSON:\n"
                f'[{{"source": "https://example.com", "content": "текст страницы"}}, ...]\n\n'
                f"Важно: верни только JSON, без дополнительных комментариев или пояснений."
            )

            queries.append({prompt: {"bank_id": bank_id, "product_id": product_id}})

    return queries


def get_bank_and_products() -> List[Dict[str, Dict[str, int]]]:
    """Получает все банки и продукты для веб-поиска"""
    banks = get_data_list("banks", "bank")
    products = get_data_list("products", "product")

    if not banks or not products:
        print("Warning: No banks or products found for search")
        return []

    return prepare_query(banks, products)


def save_raw_data(result: WebSearchResult) -> bool:
    """Сохраняет валидированные результаты поиска в таблицу bank_buffer"""
    conn = get_connection()
    ts = datetime.utcnow()
    success = False

    try:
        with conn.cursor() as cursor:
            for item in result.items:
                try:
                    # Валидация каждого элемента перед сохранением
                    validated_item = WebSearchItem(
                        source=item.source, content=item.content
                    )

                    # Просто вставляем новую запись без ON CONFLICT
                    cursor.execute(
                        """
                        INSERT INTO bank_buffer (bank_id, product_id, raw_data, source, ts)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            result.bank_id,
                            result.product_id,
                            validated_item.content,
                            validated_item.source,
                            ts,
                        ),
                    )
                except ValidationError as ve:
                    print(f"Validation error for item: {ve}")
                    continue
                except Exception as e:
                    print(f"Error saving item: {str(e)}")
                    continue

        conn.commit()
        success = True
        print(
            f"Successfully saved {len(result.items)} items for bank_id={result.bank_id}, product_id={result.product_id}"
        )

    except Exception as e:
        conn.rollback()
        print(f"Database error: {str(e)}")
    finally:
        return success

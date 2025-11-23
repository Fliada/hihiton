import json
import os
import re
from datetime import datetime
from functools import lru_cache
from os import getenv
from typing import Any, Dict, List
from urllib.parse import urljoin

import httpx
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from pydantic import ValidationError
from langchain_core.tools import tool

from src.app.domain.models import CriterionWithEmbedding, WebSearchItem, WebSearchResult

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


def save_raw_data(result: WebSearchResult) -> List[int]:
    """Сохраняет валидированные результаты поиска в таблицу bank_buffer"""
    conn = get_connection()
    ts = datetime.utcnow()
    inserted_ids: List[int] = []

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
                        RETURNING id
                        """,
                        (
                            result.bank_id,
                            result.product_id,
                            validated_item.content,
                            validated_item.source,
                            ts,
                        ),
                    )
                    row_id = cursor.fetchone()[0]
                    inserted_ids.append(row_id)
                except ValidationError as ve:
                    print(f"Validation error for item: {ve}")
                    continue
                except Exception as e:
                    print(f"Error saving item: {str(e)}")
                    continue

        conn.commit()
        if inserted_ids:
            print(
                f"Successfully saved {len(inserted_ids)} items for bank_id={result.bank_id}, product_id={result.product_id}"
            )

    except Exception as e:
        conn.rollback()
        print(f"Database error: {str(e)}")
    finally:
        return inserted_ids


@tool(parse_docstring=True)
def save_raw_web_data(bank_id: int, product_id: int, source: str, content: str) -> str:
    """
    Сохраняет один источник (source/content) в таблицу bank_buffer и возвращает ID записей.

    Args:
        bank_id: ID банка.
        product_id: ID продукта.
        source: Ссылка на источник (URL).
        content: Текстовое содержимое страницы.

    Returns:
        JSON-строка с полями status, record_ids и message. Используй record_ids, чтобы сразу вызвать
        process_raw_data_for_criteria только для добавленных записей.
    """
    try:
        payload = WebSearchResult(
            bank_id=bank_id,
            product_id=product_id,
            items=[WebSearchItem(source=source, content=content)],
        )
        record_ids = save_raw_data(payload)

        if not record_ids:
            raise ValueError("Запись не была сохранена. Проверь источник и содержимое.")

        return json.dumps(
            {
                "status": "success",
                "record_ids": record_ids,
                "message": "Сырые данные сохранены. Передайте record_ids в process_raw_data_for_criteria.",
            },
            ensure_ascii=False,
        )
    except ValidationError as ve:
        return json.dumps(
            {"status": "error", "message": f"Validation error: {ve}"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Failed to save raw data: {e}"},
            ensure_ascii=False,
        )


def get_embedding(text: str) -> List[float]:
    """Получает эмбеддинг для текста через внешний сервис"""
    embedding_url = os.getenv("EMBEDDING_SERVICE_URL")
    if not embedding_url:
        raise ValueError("EMBEDDING_SERVICE_URL is not set in environment variables")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                urljoin(embedding_url, "/dialog/nlp/embedding/paraphrase-multilingual-MiniLM-L12-v2"),
                json={"text": text},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
    except Exception as e:
        print(f"Error getting embedding: {str(e)}")
        # Возвращаем нулевой вектор как fallback
        return [0.0] * 384  # Размер по умолчанию для многих эмбеддинг-моделей


def save_processed_data(criteria_with_embeddings: List[CriterionWithEmbedding]) -> bool:
    """Сохраняет обработанные данные в таблицу bank_analysis"""
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            # Подготавливаем данные для пакетной вставки
            values = [
                (
                    criterion.bank_id,
                    criterion.product_id,
                    criterion.criterion,
                    criterion.criterion_embed,  # PostgreSQL поддерживает массивы
                    criterion.source,
                    criterion.data,
                    criterion.ts,
                )
                for criterion in criteria_with_embeddings
            ]

            execute_values(
                cursor,
                """
                INSERT INTO bank_analysis (
                    bank_id, product_id, criterion, criterion_embed, source, data, ts
                ) VALUES %s
                """,
                values,
            )

        conn.commit()
        print(
            f"Successfully saved {len(criteria_with_embeddings)} criteria to bank_analysis"
        )
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error saving processed data: {str(e)}")
        return False

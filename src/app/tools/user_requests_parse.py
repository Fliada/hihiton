from pydantic import BaseModel, Field
from fuzzywuzzy import fuzz
import psycopg2
from os import getenv
from typing import Optional, List, Dict
from app.infra.llm.client import llm

from langchain_core.tools import tool

from langchain_core.runnables import RunnableConfig

class UserRequest(BaseModel):
        bank_names: List[str] = Field(description="Список банков")
        products: List[str] = Field(description="Услуги для сравнения")
        criteria: Optional[str] = Field(
            description="Критерии сравнения услуг и банков", default=None
        )
        
data = {
    "id":1,
    "bank_id":1,
    "product_id":2,
    "criterion":"процентная ставка",
    "criterion_embed":[i for i in range(384)],
    "source":"https://www.banki.ru",
    "ts":"1",
    "data": "15 процентов"
}       
        
def get_data_list(query):
    connection = psycopg2.connect(
        host=getenv("DATABASE_HOST"),
        port=getenv("DATABASE_PORT"),
        database=getenv("DATABASE"),
        user=getenv("DATABASE_LOGIN"),
        password=getenv("DATABASE_PASSWORD"),
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return {vals: keys for keys, vals in rows}
    finally:
        connection.close()


def normalize_value_to_ids(
    values: List[str],
    candidates: Dict[str, int],  # например, Dict[str, int]
    threshold: int = 80,
) -> List[int]:
    """
    Для каждого значения из `values` находит наиболее похожий ключ в `candidates`.
    Если степень схожести >= threshold — возвращает соответствующее значение из словаря (например, id).
    Иначе — пропускает (или можно вернуть None, но обычно такие значения игнорируют).

    Args:
        values: Список строк для нормализации (например, названия банков от пользователя).
        candidates: Словарь {название: id}.
        threshold: Порог схожести (0–100).

    Returns:
        Список соответствующих значений (например, id), для которых найдено совпадение.
    """
    if not candidates:
        return []

    result_ids = []
    candidate_names = list(candidates.keys())

    for value in values:
        if not value.strip():
            continue
        best_match = max(
            candidate_names, key=lambda name: fuzz.ratio(value.lower(), name.lower())
        )
        if fuzz.ratio(value.lower(), best_match.lower()) >= threshold:
            result_ids.append(candidates[best_match])
    return result_ids


def normalize_value(
    values: List[str], candidates: Dict[str, id], threshold: int = 80
) -> str:
    """
    Приводит строку к ближайшему значению из списка вариантов, если схожесть >= threshold.
    Иначе возвращает исходную строку.
    """
    new_values = []
    if not candidates:
        return values
    for value in values:
        best_match = max(candidates, key=lambda x: fuzz.ratio(value.lower(), x.lower()))
        if fuzz.ratio(value.lower(), best_match.lower()) >= threshold:
            new_values.append(best_match)
        else:
            new_values.append(value)
    return new_values


def validate_result(query_entities: List[str], bd_entities: List[int]) -> bool:
    """
    Сравнивание кол-во полученных значений.
    """
    print(len(query_entities), len(bd_entities))
    return len(query_entities) == len(bd_entities)


@tool(parse_docstring=True)
def get_user_request_data_from_db(
    user_text: str,
    config: RunnableConfig = {"configurable": {"thread_id": ""}},
) -> dict:
    """Выделяет данные из фразы пользователя и делает по ним запрос в БД для получения информации по запросу.

    Args:
        user_text: Фраза пользователя.
    """
    reference_banks = get_data_list("SELECT * FROM banks;")
    reference_products = get_data_list("SELECT * FROM products;")
    structured_llm = llm.with_structured_output(UserRequest)

    prompt = f"Извлеки из запроса пользователя: {user_text} нужные поля для поиска информации о банках"

    try:
        result: UserRequest = structured_llm.invoke(prompt)
        print(result)
        banks = normalize_value_to_ids(result.bank_names, reference_banks)
        print(banks)
        products = normalize_value_to_ids(result.products, reference_products)
        print(products)
        if validate_result(result.bank_names, banks) and validate_result(
            result.products, products
        ):
            return {
                "bank_ids": banks,
                "product_ids": products,
                "criteria": "названия критериев оценки.",
            }
        return {
            "bank_ids": [0],
            "product_ids": [0],
            "criteria": "названия критериев оценки.",
        }
    except Exception as e:
        print(f"❌ Ошибка: {e}")

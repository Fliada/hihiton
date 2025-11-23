from pydantic import BaseModel, Field
from fuzzywuzzy import fuzz
import psycopg2
from os import getenv
from typing import Optional, List, Dict, Tuple, Any
from app.infra.llm.client import llm
from app.infra.embedder.get_embedding import get_embedding  
from itertools import product
from langchain_core.tools import tool

from langchain_core.runnables import RunnableConfig


class UserRequest(BaseModel):
    bank_names: List[str] = Field(description="Список банков")
    products: List[str] = Field(description="Услуги для сравнения")
    criteria: Optional[str] = Field(
        description="Критерии сравнения услуг и банков", default=None
    )
   
class ResultRequest(BaseModel):
    table: List[str] = Field(description="Данные csv таблицы")
    summary: List[str] = Field(description="Вывод")


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


def get_criterion_data(bank_id: int, product_id: int, embedding):
    connection = psycopg2.connect(
        host=getenv("DATABASE_HOST"),
        port=getenv("DATABASE_PORT"),
        database=getenv("DATABASE"),
        user=getenv("DATABASE_LOGIN"),
        password=getenv("DATABASE_PASSWORD"),
    )
    query = """
        SELECT
            id,
            bank_id,
            product_id,
            criterion,
            "source",
            ts,
            1 - (criterion_embed <=> %s::vector) AS cosine_similarity
        FROM
            public.bank_analysis
        WHERE
            bank_id = %s
            AND product_id = %s
        ORDER BY
            criterion_embed <=> %s::vector
        LIMIT 1;
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (embedding, bank_id, product_id, embedding))
            row = cursor.fetchone()
            print(row)
            return row
    finally:
        connection.close()


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

def get_criterion_data_for_all(
    bank_product_embeddings: List[Tuple[int, int, List[float]]]
) -> List[Tuple[Any, ...]]:
    """
    Получает наиболее релевантную запись из bank_analysis
    для каждой тройки (bank_id, product_id, embedding).
    
    Args:
        bank_product_embeddings: список вида [(bank_id, product_id, embedding), ...]
    """
    if not bank_product_embeddings:
        return []

    connection = psycopg2.connect(
        host=getenv("DATABASE_HOST"),
        port=getenv("DATABASE_PORT"),
        database=getenv("DATABASE"),
        user=getenv("DATABASE_LOGIN"),
        password=getenv("DATABASE_PASSWORD"),
    )

    try:
        with connection.cursor() as cursor:
            # Формируем VALUES: (1, 101, '[...]'::vector), (2, 102, '[...]'::vector), ...
            values_parts = []
            for bank_id, product_id, emb in bank_product_embeddings:
                emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                values_parts.append(f"({bank_id}, {product_id}, '{emb_str}'::vector)")
            
            values_clause = ", ".join(values_parts)

            # query = f"""
            #     SELECT
            #     b.bank AS bank_name,
            #     input.product_id,
            #     p.product AS product_name,
            #     ba.criterion,
            #     ba."source",
            #     ba.ts,
            #     ba.data,
            #     1 - (ba.criterion_embed <=> input.embedding) AS cosine_similarity
            # FROM
            #     (VALUES {values_clause}) AS input(bank_id, product_id, embedding)
            # LEFT JOIN LATERAL (
            #     SELECT *
            #     FROM public.bank_analysis ba2
            #     WHERE ba2.bank_id = input.bank_id
            #     AND ba2.product_id = input.product_id
            #     ORDER BY ba2.criterion_embed <=> input.embedding
            #     LIMIT 1
            # ) AS ba ON true
            # LEFT JOIN public.banks b ON b.id = input.bank_id
            # LEFT JOIN public.products p ON p.id = input.product_id
            # ORDER BY input.bank_id, input.product_id;
            # """

            query = f"""
                SELECT
                b.bank AS bank_name,
                p.product AS product_name,
                ba.criterion,
                ba.data,
                ba."source",
                ba.ts
            FROM
                (VALUES {values_clause}) AS input(bank_id, product_id, embedding)
            LEFT JOIN LATERAL (
                SELECT *
                FROM public.bank_analysis ba2
                WHERE ba2.bank_id = input.bank_id
                AND ba2.product_id = input.product_id
                ORDER BY ba2.criterion_embed <=> input.embedding
                LIMIT 1
            ) AS ba ON true
            LEFT JOIN public.banks b ON b.id = input.bank_id
            LEFT JOIN public.products p ON p.id = input.product_id
            ORDER BY input.bank_id, input.product_id;
            """
            cursor.execute(query)
            return cursor.fetchall()

    finally:
        connection.close()


@tool(parse_docstring=True)
def get_report(
    query_data: str,
    config: RunnableConfig = {"configurable": {"thread_id": ""}},
) -> dict:
    """Выделяет данные из фразы пользователя и делает по ним запрос в БД для получения информации по запросу.

    Args:
        user_text: Фраза пользователя.
    """
    reference_banks = get_data_list("SELECT * FROM banks;")
    reference_products = get_data_list("SELECT id, product FROM products;")
    structured_llm = llm.with_structured_output(UserRequest)

    prompt = f"Извлеки из запроса пользователя: {user_text} нужные поля для поиска информации о банках"

    try:
        result: UserRequest = structured_llm.invoke(prompt)
        print(result)
        banks = normalize_value_to_ids(result.bank_names, reference_banks)
        print(banks)
        products = normalize_value_to_ids(result.products, reference_products)
        print(products)
        # criterias = [result.criteria]
        criterias = ["'процентная ставка", "кешбэк"]
        # if validate_result(result.bank_names, banks) and validate_result(
        #     result.products, products
        # ):
        results = []
        csv_results = []
        for criteria in criterias:
            bank_product_embeddings = [
                (bank, product, get_embedding(criteria))
                for bank, product in product(banks, products)
            ]
            print(criteria)
            print(get_criterion_data_for_all(bank_product_embeddings))
            results.append(get_criterion_data_for_all(bank_product_embeddings))
        print("#"*50)
        import pandas as pd    
        print(results)
        all_rows = []
        for criterion_group in results:
            for row in criterion_group:
                bank, produc, metric, value, url, data = row
                print(data)
                all_rows.append({
                    'Банк': bank,
                    'Тип продукта': produc,
                    'Показатель': metric,
                    'Значение': value
                    # URL можно сохранить при необходимости, но для сводки он не нужен
                })

        # Создаём DataFrame
        df = pd.DataFrame(all_rows)
        df['Критерий'] = df['Тип продукта'] + ': ' + df['Показатель']

        # Используем pivot_table с aggfunc — например, первое значение
        pivot = df.pivot_table(
            index='Банк',
            columns='Критерий',
            values='Значение',
            aggfunc='first',          # или ','.join, если хотите объединить все значения
            fill_value=''             # заменить NaN на пустую строку
        ).reset_index()
        print(df)
        pivot.columns.name = None

        pivot.to_csv('итоговая_таблица.csv', index=False, encoding='utf-8')
        print(pivot)

        print(pivot)
        prompt = f"Составь из данных {results} csv таблицу по критериям {criterias} и банкам {result.bank_names}"
        structured_llm = llm.with_structured_output(ResultRequest)
        result: ResultRequest = structured_llm.invoke(prompt)
        print(result)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

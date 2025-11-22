from os import getenv
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

load_dotenv()


def get_data_list(table, column):
    connection = psycopg2.connect(
        host=getenv("DATABASE_HOST"),
        port=getenv("DATABASE_PORT"),
        database=getenv("DATABASE"),
        user=getenv("DATABASE_LOGIN"),
        password=getenv("DATABASE_PASSWORD"),
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT id, {column} FROM {table};")
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
    finally:
        connection.close()


def prepare_query(banks, products):
    queries = []
    for bank_id, bank in banks.items():
        for product_id, product in products.items():
            queries.append(
                {f"Найди мне в интернете информацию о {product} для банка {bank}. Ответь в формате JSON: список словарей с полями source - источник данных(ссылка), content - найденная информация": {'bank_id': bank_id, 'product_id': product_id}}
            )
    return queries


def get_bank_and_products():
    """Функция для получения информации о каждом продукте для каждого банка"

    Returns:
        Возвращает список запросов в поисковую систему.
    """
    banks = get_data_list("banks", "bank")
    products = get_data_list("products", "product")

    queries = prepare_query(banks, products)

    return queries

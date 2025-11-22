from os import getenv
from dotenv import load_dotenv
from langchain_core.tools import tool
import psycopg2

load_dotenv()

def get_data_list(table, column):
    connection = psycopg2.connect(
        host=getenv("DATABASE_HOST"),
        port=getenv("DATABASE_PORT"),
        database=getenv("DATABASE"),
        user=getenv("DATABASE_LOGIN"),
        password=getenv("DATABASE_PASSWORD")
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {column} FROM {table};")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    finally:
        connection.close()


def prepare_query(banks, products):
    queries = []
    for bank in banks:
        for product in products:
            queries.append(f"Найди мне в интернете информацию о {product} для банка {bank}")
    return queries
    
@tool(parse_docstring=True)    
def get_bank_and_products():
    banks = get_data_list("banks", "bank")
    products = get_data_list("products", "product")
    
    queries = prepare_query(banks, products)
    
    return queries
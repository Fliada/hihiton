from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from fuzzywuzzy import fuzz
import psycopg2
from os import getenv
from dotenv import load_dotenv
from typing import Optional, Literal, List
from agents.utils.llm import llm

load_dotenv()

class UserRequest(BaseModel):
    bank_names: List[str] = Field(description="Список банков")
    products: List[str] = Field(description="Услуги для сравнения")
    criteria: Optional[str] = Field(description="Критерии сравнения услуг и банков", default=None)


def get_data_list(query):
    connection = psycopg2.connect(
        host=getenv("DATABASE_HOST"),
        port=getenv("DATABASE_PORT"),
        database=getenv("DATABASE"),
        user=getenv("DATABASE_LOGIN"),
        password=getenv("DATABASE_PASSWORD")
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    finally:
        connection.close()


banks = get_data_list(f"SELECT bank FROM banks;")
products = get_data_list(f"SELECT product FROM products;")

structured_llm = llm.with_structured_output(UserRequest)

user_request = "сравни условия вкладов в сбере, уралсиб и москвачелябинвест"
prompt = f"Извлеки из запроса пользователя: {user_request} нужные поля для поиска информации о банках"

try:
    result: UserRequest = structured_llm.invoke(prompt)
    print("✅ Получен структурированный ответ:")
    print(result)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    


def normalize_value(values: List[str], candidates: List[str], threshold: int = 80) -> str:
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

print(result)
print(normalize_value(result.bank_names, banks))
print(normalize_value(result.products, products))
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from fuzzywuzzy import fuzz
import psycopg2
from typing import Optional, Literal, List
from agents.utils.llm import llm

class UserRequest(BaseModel):
    bank_names: List[str] = Field(description="Список банков")
    services: List[str] = Field(description="Услуги для сравнения")
    criteria: Optional[str] = Field(description="Критерии сравнения услуг и банков", default=None)

connection = psycopg2.connect(
        host=getenv("DATABASE_HOST"),
        port=getenv("DATABASE_PORT"),
        database=getenv("DATABASE"),
        user=getenv("DATABASE_LOGIN"),
        password=getenv("DATABASE_PASSWORD")
    )

structured_llm = llm.with_structured_output(UserRequest)

prompt = "Извлеки "

try:
    result: UserRequest = structured_llm.invoke(prompt)
    print("✅ Получен структурированный ответ:")
    print(result)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    

RECOMMENDED = ["bug", "feature", "ui", "performance", "docs"]

def normalize_categories(raw: List[str], threshold=80) -> List[str]:
    result = []
    for item in raw:
        best_match = max(RECOMMENDED, key=lambda x: fuzz.ratio(item.lower(), x))
        if fuzz.ratio(item.lower(), best_match) >= threshold:
            result.append(best_match)
        else:
            result.append(item)  # оставляем как есть
    return result
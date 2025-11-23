import logging
from os import getenv
from typing import List

import requests
from dotenv import load_dotenv

# Настройка логирования (опционально)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


def get_embedding(text: str) -> List[float]:
    """
    Получает векторное представление (embedding) для заданного текста.

    Args:
        text (str): Входной текст для векторизации.

    Returns:
        List[float]: Список чисел с плавающей точкой — embedding.

    Raises:
        ValueError: Если EMBEDDER_URL не задан или ответ сервера некорректен.
        requests.RequestException: При ошибках сети или HTTP.
    """
    if not text:
        raise ValueError("Input text cannot be empty")

    embedder_url = getenv("EMBEDDER_URL")

    try:
        response = requests.post(embedder_url, json={"text": text}, timeout=30)
        response.raise_for_status()

        data = response.json()
        embedding = data.get("embedding")

        return embedding

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise
    except ValueError as e:
        logger.error(f"Invalid response format: {e}")
        raise

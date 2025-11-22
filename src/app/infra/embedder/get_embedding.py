import requests
from os import getenv
from dotenv import load_dotenv

load_dotenv()

def get_embedding(text: str):
    response = requests.post(getenv("EMBEDDER_URL"), json={"text": text})

    if response.status_code == 200:
        data = response.json()
        embedding = data.get("embedding")
        return embedding
    else:
        print(f"Ошибка: {response.status_code}, {response.text}")
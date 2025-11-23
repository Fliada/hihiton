from fastapi import FastAPI
from src.app.api import router


def create_app() -> FastAPI:
    new_app = FastAPI(
        title="Redmine Agent API",
        description="API для ИИ-агента Redmine",
        version="1.1.0",
    )
    new_app.include_router(router)
    return new_app


app = create_app()

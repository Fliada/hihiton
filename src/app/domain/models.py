from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


class WebSearchItem(BaseModel):
    """Модель для одного источника данных из веб-поиска"""

    source: str = Field(..., description="URL источника информации")
    content: str = Field(..., description="Сырое содержимое страницы")

    @field_validator("source")
    def validate_source(cls, v):
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "Source must be a valid URL starting with http:// or https://"
            )
        if len(v) > 2000:
            raise ValueError("Source URL is too long")
        return v


class WebSearchResult(BaseModel):
    """Модель для результатов веб-поиска по паре банк-продукт"""

    bank_id: int = Field(..., gt=0, description="ID банка в базе данных")
    product_id: int = Field(..., gt=0, description="ID продукта в базе данных")
    items: List[WebSearchItem] = Field(
        ..., min_items=1, description="Список найденных источников"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Время получения данных"
    )

    @field_validator("items")
    def validate_items(cls, v):
        if not v:
            raise ValueError("Items list cannot be empty")
        return v


class CriterionWithEmbedding(BaseModel):
    bank_id: int
    product_id: int
    criterion: str
    criterion_embed: List[float]  # Вектор эмбеддинга
    source: str
    data: str
    ts: datetime

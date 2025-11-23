import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, validator
from src.app.agents.web_search_agent.tools import get_connection, get_embedding, save_processed_data

from src.app.domain.models import CriterionWithEmbedding
from src.app.infra.llm.client import llm

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


class ExtractedCriterion(BaseModel):
    criterion: str = Field(..., description="Название критерия на русском языке")
    value: str = Field(..., description="Значение критерия")

    @validator("criterion")
    def validate_criterion(cls, v):
        if not v.strip():
            raise ValueError("Criterion cannot be empty")
        return v.strip()

    @validator("value")
    def validate_value(cls, v):
        if not v.strip():
            raise ValueError("Value cannot be empty")
        return v.strip()


class CriteriaExtractionResult(BaseModel):
    criteria: List[ExtractedCriterion] = Field(
        ..., description="Список извлеченных критериев"
    )


class DataProcessor:
    def __init__(self):
        self.llm = llm
        self.structured_llm = self.llm.with_structured_output(
            CriteriaExtractionResult
        )
        self.today_date = datetime.now(timezone.utc).date()

    def get_today_raw_data(self) -> List[Dict[str, Any]]:
        """Получает сырые данные за сегодняшнее число из bank_buffer"""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                today_start = datetime.combine(
                    self.today_date, datetime.min.time(), tzinfo=timezone.utc
                )
                today_end = datetime.combine(
                    self.today_date, datetime.max.time(), tzinfo=timezone.utc
                )

                cursor.execute(
                    """
                    SELECT id, bank_id, product_id, raw_data, source, ts
                    FROM bank_buffer
                    WHERE ts >= %s AND ts <= %s
                    ORDER BY bank_id, product_id, id
                """,
                    (today_start, today_end),
                )

                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append(
                        {
                            "id": row[0],
                            "bank_id": row[1],
                            "product_id": row[2],
                            "raw_data": row[3],
                            "source": row[4],
                            "ts": row[5],
                        }
                    )

                logger.info(
                    f"Found {len(results)} raw data records for today ({self.today_date})"
                )
                return results

        except Exception as e:
            logger.error(f"Error fetching raw data from bank_buffer: {str(e)}")
            raise

    def get_bank_and_product_names(
        self, bank_id: int, product_id: int
    ) -> Tuple[str, str]:
        """Получает названия банка и продукта по их ID"""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT bank FROM banks WHERE id = %s", (bank_id,))
                bank_row = cursor.fetchone()
                bank_name = bank_row[0] if bank_row else f"bank_{bank_id}"

                cursor.execute(
                    "SELECT product FROM products WHERE id = %s", (product_id,)
                )
                product_row = cursor.fetchone()
                product_name = (
                    product_row[0] if product_row else f"product_{product_id}"
                )

                return bank_name, product_name
        except Exception as e:
            logger.error(f"Error getting bank/product names: {str(e)}")
            return f"bank_{bank_id}", f"product_{product_id}"

    def extract_criteria_from_text(
        self, raw_str, bank_name: str, product_name: str
    ) -> List[ExtractedCriterion]:
        """
        Извлекает атомарные критерии из сырого текста с помощью LLM
        """
        try:
            # Системный промпт для структурирования данных
            system_prompt = """Вы - эксперт по анализу банковских продуктов. Ваша задача - извлечь из неструктурированного текста атомарные критерии для сравнения банковских продуктов. Критерии должны соответствовать следующим требованиям:

1. Конкретные и измеримые параметры
2. Представлены в формате "название критерия" и "значение"
3. На русском языке
4. Атомарные (один критерий = одно измерение)

Правила извлечения:
- Не объединяйте несколько параметров в один критерий
- Название критерия должно быть понятным без контекста
- Значение должно содержать только саму информацию без пояснений
- Игнорируйте общие фразы и маркетинговые формулировки
- Фокусируйтесь на конкретных цифрах, процентах, сроках, суммах
- Если параметр имеет диапазон, разделяйте на мин/макс критерии
- Игнорируйте информацию об условиях получения, требованиях к заемщику, документах - фокусируйтесь только на измеримых параметрах продукта

Примеры корректных критериев:
- "максимальная сумма кредита наличными": "7000000 рублей"
- "минимальная сумма кредита наличными": "50000 рублей" 
- "срок кредита наличными": "до 7 лет"
- "минимальная процентная ставка со страхованием": "12.4%"
- "максимальная процентная ставка без страховки": "45.9%"

Примеры некорректных критериев:
- "условия кредита": "Сумма от 50000 до 7000000, срок до 7 лет"
- "ставка": "зависит от условий"
- "требования": "подтверждение дохода, возраст от 21 года"

ВАЖНО: Верните ТОЛЬКО валидный JSON в строго указанном формате без дополнительных комментариев или пояснений.
            """

            # Пользовательский промпт с контекстом
            user_prompt = f"""
БАНК: {bank_name}
ПРОДУКТ: {product_name}

СЫРЫЕ ДАННЫЕ ДЛЯ АНАЛИЗА:
{raw_str}

ЗАДАЧА: Извлеките ВСЕ возможные атомарные критерии из текста выше. Верните результат ТОЛЬКО в формате JSON:

{{
    "criteria": [
        {{
            "criterion": "название критерия",
            "value": "значение критерия"
        }},
        ...
    ]
}}

ТРЕБОВАНИЯ К ФОРМАТУ:
- Верните ТОЛЬКО валидный JSON без дополнительного текста
- Все критерии должны быть на русском языке
- Максимально детализируйте параметры (разделяйте диапазоны на отдельные критерии)
- Используйте точные формулировки из примеров корректных критериев
- Если в тексте нет измеримых параметров, верните пустой массив criteria
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.structured_llm.invoke(messages)
            logger.info(
                f"Successfully extracted {len(response.criteria)} criteria"
            )
            return response.criteria

        except Exception as e:
            logger.error(f"Error extracting criteria: {str(e)}")
            return []

    def extract_specific_criteria_from_text(
        self, raw_str, bank_name: str, product_name: str, criteria_list: List[str]
    ) -> List[ExtractedCriterion]:
        """
        Извлекает только указанные критерии из текста
        """
        try:
            if not criteria_list:
                return self.extract_criteria_from_text(raw_str, bank_name, product_name)

            criteria_str = "\n".join([f"- {criterion}" for criterion in criteria_list])

            system_prompt = f"""Вы - эксперт по анализу банковских продуктов. Ваша задача - извлечь ИЗ СПИСКА УКАЗАННЫХ КРИТЕРИЕВ те, которые присутствуют в тексте.
            
            СПИСОК КРИТЕРИЕВ ДЛЯ ПОИСКА:
            {criteria_str}
            
            Правила:
            - Извлекайте ТОЛЬКО критерии из указанного списка
            - Если критерий из списка отсутствует в тексте - не включайте его в результат
            - Значение должно быть точным и соответствовать тексту
            - Все критерии должны быть на русском языке
            - Верните ТОЛЬКО валидный JSON в формате {{"criteria": [{{"criterion": "название", "value": "значение"}}, ...]}}
            - Если ни один критерий из списка не найден, верните пустой массив criteria
            """

            user_prompt = f"""
            БАНК: {bank_name}
            ПРОДУКТ: {product_name}
            
            ТЕКСТ ДЛЯ АНАЛИЗА:
            {raw_str}
            
            ИЗВЛЕКАЙТЕ ТОЛЬКО КРИТЕРИИ ИЗ УКАЗАННОГО ВЫШЕ СПИСКА.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.structured_llm.invoke(messages)
            logger.info(
                f"Successfully extracted {len(response.criteria)} specific criteria"
            )
            return response.criteria

        except Exception as e:
            logger.error(f"Error extracting specific criteria: {str(e)}")
            return []

    def process_single_record(
        self, record: Dict[str, Any]
    ) -> List[CriterionWithEmbedding]:
        """Обрабатывает одну запись из bank_buffer"""
        try:
            bank_name, product_name = self.get_bank_and_product_names(
                record["bank_id"], record["product_id"]
            )

            # Извлекаем критерии из текста
            criteria = self.extract_criteria_from_text(
                record["raw_data"], bank_name, product_name
            )

            processed_criteria = []

            for criterion in criteria:
                try:
                    # Получаем эмбеддинг для критерия
                    embedding = get_embedding(criterion.criterion)

                    # Создаем объект для сохранения
                    processed_criteria.append(
                        CriterionWithEmbedding(
                            bank_id=record["bank_id"],
                            product_id=record["product_id"],
                            criterion=criterion.criterion,
                            criterion_embed=embedding,
                            source=record["source"],
                            data=criterion.value,
                            ts=record["ts"],
                        )
                    )

                except Exception as e:
                    logger.error(
                        f"Error processing criterion '{criterion.criterion}': {str(e)}"
                    )
                    continue

            logger.info(
                f"Processed {len(processed_criteria)} criteria for record ID {record['id']}"
            )
            return processed_criteria

        except Exception as e:
            logger.error(f"Error processing record {record['id']}: {str(e)}")
            return []

    def process_single_record_with_criteria(
        self, record: Dict[str, Any], criteria_list: Optional[List[str]] = None
    ) -> List[CriterionWithEmbedding]:
        """
        Обрабатывает одну запись с возможной фильтрацией по конкретным критериям
        """
        try:
            bank_name, product_name = self.get_bank_and_product_names(
                record["bank_id"], record["product_id"]
            )

            if criteria_list:
                # Извлекаем только указанные критерии
                criteria = self.extract_specific_criteria_from_text(
                    record["raw_data"], bank_name, product_name, criteria_list
                )
            else:
                # Извлекаем все возможные критерии
                criteria = self.extract_criteria_from_text(
                    record["raw_data"], bank_name, product_name
                )

            processed_criteria = []

            for criterion in criteria:
                try:
                    embedding = get_embedding(criterion.criterion)
                    processed_criteria.append(
                        CriterionWithEmbedding(
                            bank_id=record["bank_id"],
                            product_id=record["product_id"],
                            criterion=criterion.criterion,
                            criterion_embed=embedding,
                            source=record["source"],
                            data=criterion.value,
                            ts=record["ts"],
                        )
                    )
                except Exception as e:
                    logger.error(
                        f"Ошибка обработки критерия '{criterion.criterion}': {str(e)}"
                    )
                    continue

            return processed_criteria

        except Exception as e:
            logger.error(f"Ошибка обработки записи {record['id']}: {str(e)}")
            return []

    def process_all_today_data(self) -> bool:
        """Основная функция обработки всех данных за сегодня"""
        try:
            # Получаем сырые данные за сегодня
            raw_data_records = self.get_today_raw_data()

            if not raw_data_records:
                logger.info("No raw data found for today. Nothing to process.")
                return True

            all_processed_criteria = []

            # Обрабатываем каждую запись
            for i, record in enumerate(raw_data_records, 1):
                logger.info(
                    f"Processing record {i}/{len(raw_data_records)} (ID: {record['id']})"
                )
                processed_criteria = self.process_single_record(record)
                all_processed_criteria.extend(processed_criteria)

            if not all_processed_criteria:
                logger.warning("No criteria were extracted from any records")
                return False

            # Сохраняем все обработанные данные
            success = save_processed_data(all_processed_criteria)

            if success:
                logger.info(
                    f"Successfully processed {len(all_processed_criteria)} criteria from {len(raw_data_records)} records"
                )
            else:
                logger.error("Failed to save processed data")

            return success

        except Exception as e:
            logger.error(f"Critical error in data processing: {str(e)}")
            return False

    def process_data_with_filters(
        self,
        bank_id: Optional[int] = None,
        product_id: Optional[int] = None,
        criteria_list: Optional[List[str]] = None,
        force_today: bool = True,
    ) -> bool:
        """
        Обрабатывает данные с фильтрацией по банку, продукту и списку критериев
        """
        try:
            conn = get_connection()
            all_processed_criteria = []

            with conn.cursor() as cursor:
                # Строим запрос с фильтрацией
                query = """
                    SELECT id, bank_id, product_id, raw_data, source, ts
                    FROM bank_buffer
                    WHERE 1=1
                """
                params = []

                if force_today:
                    today_date = datetime.now(timezone.utc).date()
                    today_start = datetime.combine(
                        today_date, datetime.min.time(), tzinfo=timezone.utc
                    )
                    today_end = datetime.combine(
                        today_date, datetime.max.time(), tzinfo=timezone.utc
                    )
                    query += " AND ts >= %s AND ts <= %s"
                    params.extend([today_start, today_end])

                if bank_id is not None:
                    query += " AND bank_id = %s"
                    params.append(bank_id)

                if product_id is not None:
                    query += " AND product_id = %s"
                    params.append(product_id)

                query += " ORDER BY bank_id, product_id, id"

                cursor.execute(query, params)
                records = cursor.fetchall()

                if not records:
                    logger.info(
                        f"No records found with filters: bank_id={bank_id}, product_id={product_id}, today_only={force_today}"
                    )
                    return True

                logger.info(f"Found {len(records)} records for processing with filters")

                # Обрабатываем каждую запись
                for i, record in enumerate(records, 1):
                    record_data = {
                        "id": record[0],
                        "bank_id": record[1],
                        "product_id": record[2],
                        "raw_data": record[3],
                        "source": record[4],
                        "ts": record[5],
                    }

                    logger.info(
                        f"Processing filtered record {i}/{len(records)} (ID: {record[0]})"
                    )
                    processed_criteria = self.process_single_record_with_criteria(
                        record_data, criteria_list
                    )
                    all_processed_criteria.extend(processed_criteria)

            if not all_processed_criteria:
                logger.warning("No criteria were extracted from any filtered records")
                return False

            # Сохраняем обработанные данные
            success = save_processed_data(all_processed_criteria)

            if success:
                logger.info(
                    f"Successfully processed {len(all_processed_criteria)} criteria from filtered records"
                )
            else:
                logger.error("Failed to save processed data from filtered records")

            return success

        except Exception as e:
            logger.error(f"Error in filtered data processing: {str(e)}")
            return False

    def save_criteria_to_db(self, criteria: List[CriterionWithEmbedding]) -> bool:
        """Сохраняет критерии в базу данных"""
        return save_processed_data(criteria)

    def run(self) -> bool:
        """Запускает процесс обработки данных"""
        logger.info("Starting data processing pipeline...")
        start_time = datetime.now()

        success = self.process_all_today_data()

        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(
            f"Data processing completed in {duration.total_seconds():.2f} seconds"
        )

        return success


def main():
    """Основная функция для запуска обработчика"""
    processor = DataProcessor()
    success = processor.run()

    if success:
        logger.info("Data processing completed successfully")
    else:
        logger.error("Data processing failed")
        exit(1)


if __name__ == "__main__":
    main()

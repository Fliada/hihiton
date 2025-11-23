import logging
from datetime import datetime, timezone
from typing import List, Optional

from langchain_core.tools import tool
from src.app.agents.web_search_agent.tools import get_connection

from src.app.tools.data_processor import DataProcessor

logger = logging.getLogger(__name__)


@tool(parse_docstring=True)
def process_raw_data_for_criteria(
    bank_id: Optional[int] = None,
    product_id: Optional[int] = None,
    criteria_list: Optional[List[str]] = None,
    force_today: bool = True,
) -> str:
    """
    Обрабатывает сырые данные из bank_buffer и извлекает указанные критерии.

    Этот инструмент:
    1. Выбирает сырые данные из bank_buffer за сегодня (или все данные если force_today=False)
    2. Фильтрует по bank_id и product_id если указаны
    3. Извлекает указанные критерии из текста
    4. Генерирует эмбеддинги и сохраняет в bank_analysis

    Args:
        bank_id: ID банка для фильтрации (необязательно)
        product_id: ID продукта для фильтрации (необязательно)
        criteria_list: Список конкретных критериев для извлечения (необязательно)
        force_today: Обрабатывать только сегодняшние данные (по умолчанию True)

    Returns:
        str: Статус обработки с количеством обработанных записей
    """
    try:
        processor = DataProcessor()

        # Фильтрация данных
        today_date = datetime.now(timezone.utc).date() if force_today else None

        conn = get_connection()
        processed_records = 0
        total_criteria = 0

        with conn.cursor() as cursor:
            # Строим запрос с фильтрацией
            query = """
                SELECT id, bank_id, product_id, raw_data, source, ts
                FROM bank_buffer
                WHERE 1=1
            """
            params = []

            if today_date:
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
                return f"Не найдено сырых данных для обработки. Параметры: bank_id={bank_id}, product_id={product_id}, today_only={force_today}"

            logger.info(f"Найдено {len(records)} записей для обработки")

            # Обрабатываем каждую запись
            for record in records:
                record_data = {
                    "id": record[0],
                    "bank_id": record[1],
                    "product_id": record[2],
                    "raw_data": record[3],
                    "source": record[4],
                    "ts": record[5],
                }

                # Извлекаем критерии
                processed_criteria = processor.process_single_record_with_criteria(
                    record_data, criteria_list
                )

                if processed_criteria:
                    # Сохраняем обработанные данные
                    success = processor.save_criteria_to_db(processed_criteria)
                    if success:
                        processed_records += 1
                        total_criteria += len(processed_criteria)
                        logger.info(
                            f"Обработано {len(processed_criteria)} критериев для записи ID {record[0]}"
                        )

        result = f"Успешно обработано {processed_records} записей с {total_criteria} критериями"
        if bank_id or product_id or criteria_list:
            result += f"\nФильтры: bank_id={bank_id}, product_id={product_id}, criteria={criteria_list}"

        return result

    except Exception as e:
        logger.error(f"Ошибка в process_raw_data_for_criteria: {str(e)}")
        return f"Критическая ошибка при обработке данных: {str(e)}"

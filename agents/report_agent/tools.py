import psycopg2


def get_filtered_data(filter_columns):
    """
    filter_columns — dict, где ключи это названия колонок,
    а значения — значения для фильтрации.
    Например:
    {
        "status": "active",
        "country": "RU"
    }
    """

    # Подключение к PostgreSQL (пример с реальными значениями)
    conn = psycopg2.connect(
        dbname="testdb",
        user="testuser",
        password="testpass",
        host="localhost",
        port="5432",
    )

    cursor = conn.cursor()

    # Формируем WHERE динамически
    where_parts = []
    params = []
    for col, val in filter_columns.items():
        where_parts.append(f"{col} = %s")
        params.append(val)

    where_clause = ""
    if where_parts:
        where_clause = " WHERE " + " AND ".join(where_parts)

    query = f"""
        SELECT *
        FROM users
        {where_clause};
    """

    cursor.execute(query, params)
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]

    cursor.close()
    conn.close()

    # Преобразуем каждую строку в строку "ключ=значение; ключ=значение; ..."
    results = []
    for row in rows:
        pairs = []
        for name, value in zip(colnames, row):
            pairs.append(f"{name}={value}")
        results.append("; ".join(pairs))

    # Возвращаем одну объединённую строку
    return "\n".join(results)


# Пример использования:
filters = {"status": "active", "country": "RU"}

print(get_filtered_data(filters))

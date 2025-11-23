import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Ваши данные
data = [
    [
        ('15', datetime.datetime(2025, 11, 22, 19, 35, 29, 956606, tzinfo=datetime.timezone.utc)),
        ('18',  datetime.datetime(2025, 11, 22, 21, 14, 0, 318237, tzinfo=datetime.timezone.utc))
    ]
]
data = [[('Сбер', 'накопительные счета', 'процентная ставка', '15 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 19, 35, 29, 956606, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'процентная ставка', '18 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 21, 14, 0, 318237, tzinfo=datetime.timezone.utc))], [('Сбер', 'накопительные счета', 'кэшбек', '9 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 23, 313438, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'кэшбек', '8 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 14, 605646, tzinfo=datetime.timezone.utc))]]
all_records = [item for sublist in data for item in sublist]

# Шаг 2: Группировка по банку
bank_groups = defaultdict(list)
for record in all_records:
    bank = record[0]
    bank_groups[bank].append(record)

# Шаг 3: Обработать каждую группу
result = {}

for bank, records in bank_groups.items():
    # Возьмём первые три поля из первой записи для формирования заголовка
    # (предполагаем, что они одинаковы для всех записей по банку — или хотя бы тип и показатель совпадают)
    _, account_type, metric = records[0][1], records[0][2], records[0][3]
    # Формируем заголовок: "Сбер накопительные счета : процентная ставка"
    title = f"{bank} {account_type} : {metric}"

final_groups = {}

for (bank, acc_type, metric), items in grouped.items():
    cleaned_items = []
    for value_str, dt in items:
        num = extract_number(value_str)
        if num is not None:
            # Убираем tzinfo для matplotlib (опционально)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            cleaned_items.append((num, dt))
    title = f"{bank} {acc_type} : {metric}"
    final_groups[title] = cleaned_items

# Теперь final_groups содержит всё, что нужно
for title, data_points in final_groups.items():
    print(f"\n=== {title} ===")
    for val, dt in data_points:
        print(f"  {val} → {dt}")

# # Извлекаем (значение, дата)
# rows = []
# for group in data:
#     for item in group:
#         value_str = item[0]
#         timestamp = item[-1]  # всегда последний элемент — дата
#         try:
#             value = float(value_str)
#         except (ValueError, TypeError):
#             continue
#         # Убираем временную зону для простоты (опционально)
#         if timestamp.tzinfo is not None:
#             timestamp = timestamp.replace(tzinfo=None) # локальное время без tz
#         rows.append({'date': timestamp, 'value': value})

# df = pd.DataFrame(rows)
# df = df.sort_values('date').reset_index(drop=True)
# print(df)
# # График
# plt.figure(figsize=(10, 5))
# plt.plot(df['date'], df['value'], marker='o', linewidth=2, markersize=6)

# # Форматирование оси X
# plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M'))
# plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
# plt.xticks(rotation=0)

# plt.xlabel('Дата и время')
# plt.ylabel('Значение (%)')
# plt.title('Динамика показателя')
# plt.grid(True, linestyle='--', alpha=0.6)
# plt.tight_layout()

# # Сохраняем
# plt.savefig('график.png', dpi=200)
# print("График сохранён как 'график.png'")
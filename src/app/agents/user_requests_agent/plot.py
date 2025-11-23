import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
from datetime import timezone
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
data = [[('Сбер', 'накопительные счета', 'процентная ставка', '15 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 19, 35, 29, 956606, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'процентная ставка', '18 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 21, 14, 0, 318237, tzinfo=datetime.timezone.utc))], [('Сбер', 'накопительные счета', 'процентная ставка', '9 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 23, 313438, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'процентная ставка', '8 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 14, 605646, tzinfo=datetime.timezone.utc))]]
data = [[('Сбер', 'накопительные счета', 'процентная ставка', '15 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 19, 35, 29, 956606, tzinfo=datetime.timezone.utc)), ('Сбер', 'накопительные счета', 'кэшбек', '9 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 23, 313438, tzinfo=datetime.timezone.utc)), ('Сбер', 'накопительные счета', 'кэшбек', '19 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 1, 18, 12, 16337, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'процентная ставка', '18 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 21, 14, 0, 318237, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'кэшбек', '8 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 14, 605646, tzinfo=datetime.timezone.utc))], [('Сбер', 'накопительные счета', 'кэшбек', '9 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 23, 313438, tzinfo=datetime.timezone.utc)), ('Сбер', 'накопительные счета', 'кэшбек', '19 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 1, 18, 12, 16337, tzinfo=datetime.timezone.utc)), ('Сбер', 'накопительные счета', 'процентная ставка', '15 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 19, 35, 29, 956606, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'кэшбек', '8 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 23, 0, 27, 14, 605646, tzinfo=datetime.timezone.utc)), ('ОТП Банк', 'накопительные счета', 'процентная ставка', '18 процентов', 'https://www.banki.ru', datetime.datetime(2025, 11, 22, 21, 14, 0, 318237, tzinfo=datetime.timezone.utc))]]
data = [[('Альфа-Банк', 'накопительные счета', 'ограничения на пополнение накопительного счета', 'нет ограничений', 'https://alfabank.ru/make-money/savings-account/', datetime.datetime(2025, 11, 23, 1, 13, 6, 982580, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'минимальная сумма для открытия накопительного счета', '1 рубль', 'https://alfabank.ru/make-money/savings-account/', datetime.datetime(2025, 11, 23, 1, 13, 6, 982580, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'минимальная сумма для открытия накопительного счета', '1 рубль', 'https://alfabank.ru/make-money/', datetime.datetime(2025, 11, 23, 1, 8, 31, 391326, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'наличие комиссии за обслуживание накопительного счета', 'бесплатно', 'https://alfabank.ru/make-money/savings-account/', datetime.datetime(2025, 11, 23, 1, 13, 6, 982580, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'частота начисления процентов по накопительному счету', 'ежедневно', 'https://alfabank.ru/make-money/savings-account/', datetime.datetime(2025, 11, 23, 1, 13, 6, 982580, tzinfo=datetime.timezone.utc))], [ ('Альфа-Банк', 'накопительные счета', 'максимальная процентная ставка по накопительному счету', '17% годовых', 'https://alfabank.ru/make-money/savings-account/', datetime.datetime(2025, 11, 23, 1, 13, 6, 982580, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'максимальная процентная ставка по накопительному счёту', '17% годовых', 'https://alfabank.ru/help/articles/deposits/chto-takoe-nakopitelnyj-schet/', datetime.datetime(2025, 11, 23, 1, 13, 6, 982580, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'максимальная процентная ставка по накопительному счёту', '17% годовых', 'https://alfabank.ru/make-money/savings-account/', datetime.datetime(2025, 11, 23, 1, 8, 31, 391326, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'максимальная процентная ставка по накопительному счету по ежедневному остатку', '17% годовых', 'https://alfabank.ru/make-money/', datetime.datetime(2025, 11, 23, 1, 8, 31, 391326, tzinfo=datetime.timezone.utc)), ('Альфа-Банк', 'накопительные счета', 'минимальная сумма для открытия накопительного счета', '1 рубль', 'https://alfabank.ru/make-money/', datetime.datetime(2025, 11, 23, 1, 8, 31, 391326, tzinfo=datetime.timezone.utc))]]
# === 1. Объединяем все записи из всех подсписков ===
all_records = [record for sublist in data for record in sublist]
if not all_records:
    raise ValueError("Нет данных для отображения")

# Берём метаданные из первой записи (предполагается, что все записи однородны)
_, product_type, metric_name = all_records[0][0], all_records[0][1], all_records[0][2]
common_ylabel = metric_name  # например: "процентная ставка"
common_title = f"{product_type}: {metric_name}"

# === 2. Группировка по банку ===
grouped = defaultdict(list)
for record in all_records:
    bank = record[0]
    grouped[bank].append(record)

# === 3. Подготовка временных рядов ===
bank_series = {}

def extract_number(value_str):
    """Извлекает первое число с плавающей точкой из строки. Возвращает float или None."""
    match = re.search(r'[-+]?\d*\.?\d+', value_str)
    return float(match.group()) if match else None

for bank, records in grouped.items():
    series = []
    for rec in records:
        value_str = rec[3]
        num = extract_number(value_str)
        if num is not None:  # пропускаем записи без чисел
            series.append((rec[5], num))  # (дата, значение)
    if series:  # сохраняем банк только если есть хотя бы одна валидная запись
        series.sort(key=lambda x: x[0])  # сортировка по времени
        bank_series[bank] = series

# Проверка, что после фильтрации остались данные
if not bank_series:
    raise ValueError("Нет данных с числовыми значениями для построения графика")

# === 4. Построение графика ===
plt.figure(figsize=(12, 6))

for bank, series in bank_series.items():
    dates, values = zip(*series)
    plt.plot(dates, values, marker='o', linewidth=2, markersize=6, label=bank)

# Динамическое оформление — без хардкода!
plt.title(common_title, fontsize=14)
plt.xlabel("Дата", fontsize=12)          # ← единственные "хардкодные" слова
plt.ylabel(common_ylabel, fontsize=12)   # ← всё остальное — из данных
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(title="Банки")

# Форматирование оси X
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=6))
plt.gcf().autofmt_xdate()

# Сохранение
output_filename = f"{product_type.replace(' ', '_')}_{metric_name.replace(' ', '_')}.png"
plt.tight_layout()
plt.savefig(r"app\resourses\plot.png", dpi=150)
plt.close()


print(f"✅ График сохранён как '{output_filename}'")





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
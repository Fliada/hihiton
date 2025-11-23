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

# Извлекаем (значение, дата)
rows = []
for group in data:
    for item in group:
        value_str = item[0]
        timestamp = item[-1]  # всегда последний элемент — дата
        try:
            value = float(value_str)
        except (ValueError, TypeError):
            continue
        # Убираем временную зону для простоты (опционально)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None) # локальное время без tz
        rows.append({'date': timestamp, 'value': value})

df = pd.DataFrame(rows)
df = df.sort_values('date').reset_index(drop=True)
print(df)
# График
plt.figure(figsize=(10, 5))
plt.plot(df['date'], df['value'], marker='o', linewidth=2, markersize=6)

# Форматирование оси X
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M'))
plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
plt.xticks(rotation=0)

plt.xlabel('Дата и время')
plt.ylabel('Значение (%)')
plt.title('Динамика показателя')
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()

# Сохраняем
plt.savefig('график.png', dpi=200)
print("График сохранён как 'график.png'")
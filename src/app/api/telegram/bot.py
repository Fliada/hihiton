import asyncio
import base64
import json
import logging
from os import getenv

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile, BufferedInputFile
from aiogram.filters import Command
from aiogram.filters import CommandStart
import aiohttp

from src.app.agents.user_requests_agent.run import run_agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

telegram_token = getenv("TELEGRAM_API_TOKEN")

if telegram_token:
    bot = Bot(token=telegram_token)
    dp = Dispatcher()
else:
    bot = None
    dp = Dispatcher()
    logger.warning(
        "TELEGRAM_API_TOKEN is not set. Telegram bot is disabled; "
        "web frontend/API can be tested without this token."
    )


async def send_long_message(chat_id: int, text: str):
    if len(text) <= 4000:
        await bot.send_message(chat_id=chat_id, text=text)
        return

    parts = []
    current_part = ""
    for line in text.split("\n"):
        if len(current_part) + len("\n") + len(line) <= 4000:
            current_part += "\n" + line
        else:
            if current_part:
                parts.append(current_part.lstrip("\n"))
            current_part = line

    if current_part:
        parts.append(current_part)

    for part in parts:
        if part:
            await bot.send_message(chat_id=chat_id, text=part)
            await asyncio.sleep(0.1)

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    """Обработка команды /start."""
    await message.answer("Привет! Введите ваш запрос.")


@dp.message()
async def handle_user_message(message: types.Message):
    if bot is None:
        await message.answer("Бот отключен: TELEGRAM_API_TOKEN не задан.")
        return
    user_id = message.from_user.id
    user_text = message.text.strip()

    await message.answer("Обрабатываю ваше сообщение...")

    result = run_agent(user_text, "")
    result = result["messages"][-1].content
    
    try:
        result = json.loads(result)
        text = result['text']
        csv = result.get("csv")
        png = result.get("png")
    except json.JSONDecodeError:
        text = result
        csv = None
        png = None
    # Отправляем текст
    await send_long_message(user_id, text)

    # Отправляем CSV если нужно
    if csv:
        csv_path = "src/app/resourses/report.csv"
        csv_file = FSInputFile(csv_path)
        await bot.send_document(user_id, csv_file, caption="CSV-файл")

    # Отправляем PNG если нужно
    if png:
        png_path = "src/app/resourses/plot.png"
        png_file = FSInputFile(png_path)
        await bot.send_photo(user_id, png_file, caption="Изображение")


async def main():
    if bot is None:
        logger.error("TELEGRAM_API_TOKEN не задан. Телеграм-бот не будет запущен.")
        return

    logger.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

# async def send_to_api(user_message: str, user_id: int):
#     payload = {"message": user_message}
#     headers = {"Content-Type": "application/json"}

#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.post(getenv("TARGET_API_URL"), json=payload, headers=headers) as response:

#                 if response.status != 200:
#                     await bot.send_message(user_id, f"Ошибка API: {response.status}")
#                     return

#                 api_resp = await response.json()

#                 text = api_resp["text"]
#                 send_csv = api_resp["send_csv"]
#                 send_png = api_resp["send_png"]

#                 # ---- отправляем текст ----
#                 await send_long_message(user_id, text)

#                 # ---- CSV ----
#                 if send_csv:
#                     try:
#                         csv_file = FSInputFile("files/report.csv")
#                         await bot.send_document(user_id, csv_file, caption="CSV-файл")
#                     except Exception as e:
#                         await bot.send_message(user_id, f"Ошибка отправки CSV: {e}")

#                 # ---- PNG ----
#                 if send_png:
#                     try:
#                         png_file = FSInputFile("files/image.png")
#                         await bot.send_photo(user_id, png_file, caption="Изображение")
#                     except Exception as e:
#                         await bot.send_message(user_id, f"Ошибка отправки PNG: {e}")

#     except Exception as e:
#         await bot.send_message(user_id, f"Ошибка API: {e}")


# # ====== НОВОЕ: отправка CSV-файла ======
# @dp.message(Command("csv"))
# async def send_csv_file(message: types.Message):
#     """
#     Отправляет готовый CSV-файл report.csv, лежащий рядом со скриптом.
#     """
#     try:
#         csv_file = FSInputFile("report.csv")
#         await message.answer_document(csv_file, caption="Вот ваш CSV-файл report.csv")
#     except Exception as e:
#         logger.error(f"Error sending CSV file: {e}")
#         await message.answer("Не удалось отправить CSV-файл. Проверь, что report.csv лежит рядом с ботом.")


# # ====== НОВОЕ: отправка изображения ======
# @dp.message(Command("image"))
# async def send_image_file(message: types.Message):
#     """
#     Отправляет изображение image.png, лежащее рядом со скриптом.
#     """
#     try:
#         image_file = FSInputFile("image.png")
#         await message.answer_photo(image_file, caption="Вот изображение image.png")
#     except Exception as e:
#         logger.error(f"Error sending image file: {e}")
#         await message.answer("Не удалось отправить изображение. Проверь, что image.png лежит рядом с ботом.")


# # ====== ПРИМЕР: отправка CSV, сформированного в памяти ======
# @dp.message(Command("csv_dynamic"))
# async def send_dynamic_csv(message: types.Message):
#     """
#     Пример: формируем CSV "на лету" и отправляем без сохранения на диск.
#     """
#     csv_text = "id,name,amount\n1,Rustam,100\n2,Test,250\n"
#     csv_bytes = csv_text.encode("utf-8")

#     csv_buffer = BufferedInputFile(csv_bytes, filename="dynamic_report.csv")
#     await message.answer_document(csv_buffer, caption="Динамически сгенерированный CSV-файл")


# # ====== основной обработчик текстовых сообщений (как у тебя было) ======

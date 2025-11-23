import asyncio
import json
import logging
from os import getenv

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import CommandStart

from src.app.agents.user_requests_agent.run import run_agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=getenv("TELEGRAM_API_TOKEN"))
dp = Dispatcher()


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
    user_id = message.from_user.id
    user_text = message.text.strip()

    await message.answer("Обрабатываю ваше сообщение...")

    result = run_agent(user_text)
    result = result["messages"][-1].content

    try:
        result = json.loads(result)
        text = result["text"]
        csv = result.get("csv")
        png = result.get("png")
    except json.JSONDecodeError:
        text = result
        csv = None
        png = None
    await send_long_message(user_id, text)

    if csv:
        csv_path = "src/app/resourses/report.csv"
        csv_file = FSInputFile(csv_path)
        await bot.send_document(user_id, csv_file, caption="CSV-файл")

    if png:
        png_path = "src/app/resourses/plot.png"
        png_file = FSInputFile(png_path)
        await bot.send_photo(user_id, png_file, caption="Изображение")


async def main():
    logger.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

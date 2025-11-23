import asyncio
import logging
from os import getenv

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
import aiohttp

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


async def send_to_api(user_message: str, user_id: int):
    """Функция для отправки сообщения пользователя на внешнее API с общим ключом."""
    payload = {
        "message": user_message,
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(getenv("TARGET_API_URL"), json=payload, headers=headers) as response:
                if response.status == 200:
                    api_response = await response.json()

                    response_text = api_response["response"]
                    await send_long_message(chat_id=user_id, text=response_text)
                else:
                    logger.error(f"API request failed with status {response.status}")
                    await bot.send_message(user_id, f"Ошибка API: {response.status}")
    except aiohttp.ClientError as e:
        logger.error(f"Network error during API call: {e}")
        await bot.send_message(user_id, "Ошибка при обращении к API.")
    except Exception as e:
        logger.error(f"Unexpected error during API call: {e}")
        await bot.send_message(user_id, "Произошла непредвиденная ошибка при обработке запроса к API.")
       
        
@dp.message()
async def handle_user_message(message: types.Message):
    """Обработка сообщений от пользователя."""
    user_id = message.from_user.id
    user_input = message.text.strip()

    await message.answer("Обрабатываю ваше сообщение...")
    asyncio.create_task(send_to_api(user_input, user_id))


async def main():
    logger.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == 'main':
    asyncio.run(main())
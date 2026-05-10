import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# Append shared path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
import database as db

from handlers import router

logging.basicConfig(level=logging.INFO)

async def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    bot_token = os.getenv("PSYCH_BOT_TOKEN")
    if not bot_token:
        logging.error("No PSYCH_BOT_TOKEN found in environment variables.")
        return

    # Initialize DB (can be called by either bot)
    await db.init_db()

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    logging.info("Starting Psychologist bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

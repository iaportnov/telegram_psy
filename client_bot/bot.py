import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

import sys

# Append shared path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
import database as db
from handlers import router

# Configure logging
logging.basicConfig(level=logging.INFO)

async def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    bot_token = os.getenv("CLIENT_BOT_TOKEN")
    if not bot_token:
        logging.error("No CLIENT_BOT_TOKEN found in environment variables.")
        return

    # Initialize DB
    await db.init_db()

    # Initialize Bot and Dispatcher
    bot = Bot(token=bot_token)
    dp = Dispatcher()

    # Include routers
    dp.include_router(router)

    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

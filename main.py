# main.py
import asyncio
import logging
from src.bot import DigitalShopBot
from src.config import setup_logging

async def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize and start bot
        bot = DigitalShopBot()
        logger.info("Starting bot...")
        await bot.start()
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())

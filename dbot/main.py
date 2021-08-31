import asyncio
import logging
import time

from erepublik.constants import COUNTRIES

from dbot.base import ADMIN_ID, DB, DB_NAME, DEFAULT_CHANNEL_ID, DISCORD_TOKEN, LOOP, PRODUCTION, logger
from dbot.bot import bot
from dbot.client import client

if PRODUCTION:
    logger.warning("Production mode enabled!")
    logger.setLevel(logging.INFO)
    _ts = int(time.time())
    for c_id in COUNTRIES.keys():
        DB.set_rss_feed_timestamp(c_id, _ts)
    del _ts

logger.debug(f"Active configs:\nDISCORD_TOKEN='{DISCORD_TOKEN}'\nDEFAULT_CHANNEL_ID='{DEFAULT_CHANNEL_ID}'\nADMIN_ID='{ADMIN_ID}'\nDB_NAME='{DB_NAME}'")


def main():

    logger.info("Starting Bot loop")
    LOOP.create_task(bot.start(DISCORD_TOKEN))
    # asyncio.run(bot.start(DISCORD_TOKEN))

    logger.info("Starting Client loop")
    # asyncio.run(client.start(DISCORD_TOKEN))
    LOOP.create_task(client.start(DISCORD_TOKEN))

    LOOP.run_forever()


async def run_main():
    logger.info("Starting Client loop")
    logger.info("Starting Bot loop")
    await asyncio.gather(bot.start(DISCORD_TOKEN), client.start(DISCORD_TOKEN))
    logger.info("Loops have finished")


if __name__ == "__main__":
    # asyncio.run(run_main())
    main()

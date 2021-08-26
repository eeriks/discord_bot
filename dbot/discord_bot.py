import asyncio
import datetime
import logging
import time

import discord
import feedparser
import pytz
import requests
from constants import events
from erepublik.constants import COUNTRIES

from dbot.base import ADMIN_ID, DB, DB_NAME, DEFAULT_CHANNEL_ID, DISCORD_TOKEN, PRODUCTION, logger
from dbot.bot_commands import bot
from dbot.utils import check_battles, get_battle_page, timestamp

if PRODUCTION:
    logger.warning("Production mode enabled!")
    logger.setLevel(logging.INFO)
    _ts = int(time.time())
    for c_id in COUNTRIES.keys():
        DB.set_rss_feed_timestamp(c_id, _ts)
    del _ts

logger.debug(f"Active configs:\nDISCORD_TOKEN='{DISCORD_TOKEN}'\nDEFAULT_CHANNEL_ID='{DEFAULT_CHANNEL_ID}'\nADMIN_ID='{ADMIN_ID}'\nDB_NAME='{DB_NAME}'")


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # create the background task and run it in the background
        self.last_event_timestamp = timestamp()

    async def on_ready(self):
        logger.info("Client running")
        logger.info("------")
        self.bg_task = self.loop.create_task(self.report_battle_events())
        # self.bg_rss_task = self.loop.create_task(self.report_rss_events())

    async def on_error(self, event_method, *args, **kwargs):
        logger.warning(f"Ignoring exception in {event_method}")

    async def send_msg(self, channel_id, *args, **kwargs):
        if PRODUCTION:
            return self.get_channel(channel_id).send(*args, **kwargs)
        else:
            return logger.debug(f"Sending message to: {channel_id}\nArgs: {args}\nKwargs{kwargs}")

    async def report_rss_events(self):
        await self.wait_until_ready()
        feed_response = None
        while not self.is_closed():
            try:
                for country in COUNTRIES.values():
                    latest_ts = DB.get_rss_feed_timestamp(country.id)
                    rss_link = f"https://www.erepublik.com/en/main/news/military/all/{country.link}/1/rss"
                    feed_response = requests.get(rss_link)
                    feed_response.raise_for_status()
                    for entry in reversed(feedparser.parse(feed_response.text).entries):
                        entry_ts = time.mktime(entry["published_parsed"])
                        entry_link = entry["link"]
                        # Check if event timestamp is after latest processed event for country
                        if entry_ts > latest_ts:
                            DB.set_rss_feed_timestamp(country.id, entry_ts)
                            title = text = ""
                            msg = entry["summary"]
                            dont_send = False
                            for kind in events:
                                match = kind.regex.search(msg)
                                if match:
                                    values = match.groupdict()
                                    # Special case for Dictator/Liberation wars
                                    if "invader" in values and not values["invader"]:
                                        values["invader"] = values["defender"]

                                    # Special case for resource concession
                                    if "link" in values:
                                        __link = values["link"]
                                        entry_link = __link if __link.startswith("http") else f"https://www.erepublik.com{__link}"
                                        logger.debug(kind.format.format(**dict(match.groupdict(), **{"current_country": country.name})))
                                        logger.debug(entry_link)
                                    is_latvia = country.id == 71
                                    has_latvia = any("Latvia" in v for v in values.values())
                                    if is_latvia or has_latvia:
                                        text = kind.format.format(**dict(match.groupdict(), **{"current_country": country.name}))
                                        title = kind.name
                                    else:
                                        dont_send = True
                                    break
                            else:
                                logger.warning(f"Unable to parse: {str(entry)}")
                                continue

                            if dont_send:
                                continue

                            entry_datetime = datetime.datetime.fromtimestamp(entry_ts, pytz.timezone("US/Pacific"))
                            embed = discord.Embed(title=title, url=entry_link, description=text)
                            embed.set_author(name=country.name, icon_url=f"https://www.erepublik.com/images/flags/L/{country.link}.gif")
                            embed.set_footer(text=f"{entry_datetime.strftime('%F %T')} (eRepublik time)")

                            logger.debug(f"Message sent: {text}")
                            for channel_id in DB.get_kind_notification_channel_ids("events"):
                                await self.get_channel(channel_id).send(embed=embed)
            except Exception as e:
                logger.error("eRepublik event reader ran into a problem!", exc_info=e)
                try:
                    with open(f"debug/{timestamp()}.rss", "w") as f:
                        f.write(feed_response.text)
                except (NameError, AttributeError):
                    logger.error("There was no Response object!", exc_info=e)
            finally:
                await asyncio.sleep((timestamp() // 300 + 1) * 300 - timestamp())

    async def report_battle_events(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                r = get_battle_page()
                if not isinstance(r.get("battles"), dict):
                    sleep_seconds = r.get("last_updated") + 60 - timestamp()
                    await asyncio.sleep(sleep_seconds if sleep_seconds > 0 else 0)
                    continue

                desc = "'Empty' medals are being guessed based on the division wall. Expect false-positives!"
                empty_divisions = {
                    1: discord.Embed(title="Possibly empty **__last-minute__ D1** medals", description=desc),
                    2: discord.Embed(title="Possibly empty **__last-minute__ D2** medals", description=desc),
                    3: discord.Embed(title="Possibly empty **__last-minute__ D3** medals", description=desc),
                    4: discord.Embed(title="Possibly empty **__last-minute__ D4** medals", description=desc),
                    11: discord.Embed(title="Possibly empty **__last-minute__ Air** medals", description=desc),
                }
                for kind, div, data in check_battles(r.get("battles")):
                    if kind == "epic" and not DB.check_epic(data["div_id"]):
                        embed_data = dict(
                            title=" ".join(data["extra"]["intensity_scale"].split("_")).title(),
                            url=data["url"],
                            description=f"Epic battle {' vs '.join(data['sides'])}!\nBattle for {data['region']}, Round {data['zone_id']}",
                            footer=f"Round time {data['round_time']}",
                        )
                        embed = discord.Embed.from_dict(embed_data)
                        logger.debug(f"{embed_data=}")
                        for channel_id in DB.get_kind_notification_channel_ids("epic"):
                            if role_id := DB.get_role_id_for_channel_division(kind="epic", channel_id=channel_id, division=div):
                                await self.get_channel(channel_id).send(f"<@&{role_id}> epic battle detected!", embed=embed)
                            else:
                                await self.get_channel(channel_id).send(embed=embed)
                        DB.add_epic(data["div_id"])

                    if kind == "empty" and data["round_time_s"] >= 85 * 60 and not DB.check_empty_medal(data["div_id"]):
                        empty_divisions[div].add_field(
                            name=f"**Battle for {data['region']} {' '.join(data['sides'])}**", value=f"[R{data['zone_id']} | Time {data['round_time']}]({data['url']})"
                        )
                        DB.add_empty_medal(data["div_id"])
                for d, e in empty_divisions.items():
                    if e.fields:
                        for channel_id in DB.get_kind_notification_channel_ids("empty"):
                            if role_id := DB.get_role_id_for_channel_division(kind="empty", channel_id=channel_id, division=d):
                                await self.get_channel(channel_id).send(f"<@&{role_id}> empty medals in late rounds!", embed=e)
                            else:
                                await self.get_channel(channel_id).send(embed=e)
                sleep_seconds = r.get("last_updated") + 60 - timestamp()
                await asyncio.sleep(sleep_seconds if sleep_seconds > 0 else 0)
            except Exception as e:
                logger.error("Discord bot's eRepublik epic watcher died!", exc_info=e)
                try:
                    with open(f"debug/{timestamp()}.json", "w") as f:
                        f.write(f"{r}")
                except NameError:
                    logger.error("There was no Response object!", exc_info=e)
                await asyncio.sleep(10)
        await self.get_channel(DEFAULT_CHANNEL_ID).send(f"<@{ADMIN_ID}> I've stopped, please restart")


loop = asyncio.get_event_loop()
client = MyClient()


def main():
    global loop
    logger.info("Starting Bot loop")
    loop.create_task(bot.start(DISCORD_TOKEN))
    logger.info("Starting Client loop")
    loop.create_task(client.start(DISCORD_TOKEN))
    loop.run_forever()


if __name__ == "__main__":
    main()

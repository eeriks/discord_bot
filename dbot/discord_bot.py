import asyncio
import datetime
import logging
import os
import sys
import time
from json import JSONDecodeError

import discord
import feedparser
import pytz
import requests
from discord.ext import commands
from erepublik.constants import COUNTRIES

from constants import events
from db import DiscordDB
from dbot.utils import timestamp, check_battles

APP_NAME = "discord_bot"

os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
os.makedirs("debug", exist_ok=True)

logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

file_logger = logging.FileHandler("debug/logging.log", "w")
file_logger.setLevel(logging.WARNING)
file_logger.setFormatter(formatter)
logger.addHandler(file_logger)

stream_logger = logging.StreamHandler()
stream_logger.setLevel(logging.DEBUG)
stream_logger.setFormatter(formatter)
logger.addHandler(stream_logger)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_CHANNEL_ID = os.getenv("DEFAULT_CHANNEL_ID", 603527159109124096)
ADMIN_ID = os.getenv("ADMIN_ID", 220849530730577920)
DB_NAME = os.getenv("DB_NAME", "discord.db")
PRODUCTION = bool(os.getenv("PRODUCTION"))
DB = DiscordDB(DB_NAME)

if PRODUCTION:
    logger.warning("Production mode enabled!")
    logger.setLevel(logging.INFO)
    _ts = int(time.time())
    for c_id in COUNTRIES.keys():
        DB.set_rss_feed_timestamp(c_id, _ts)
    del _ts

logger.debug(f"Active configs:\nDISCORD_TOKEN='{DISCORD_TOKEN}'\nDEFAULT_CHANNEL_ID='{DEFAULT_CHANNEL_ID}'\nADMIN_ID='{ADMIN_ID}'\nDB_NAME='{DB_NAME}'")

MENTION_MAPPING = {1: "D1", 2: "D2", 3: "D3", 4: "D4", 11: "Air"}

__last_battle_response = None
__last_battle_update_timestamp = 0


def get_battle_page():
    global __last_battle_update_timestamp, __last_battle_response
    if int(datetime.datetime.now().timestamp()) >= __last_battle_update_timestamp + 60:
        dt = datetime.datetime.now()
        r = requests.get("https://www.erepublik.com/en/military/campaignsJson/list")
        try:
            __last_battle_response = r.json()
        except JSONDecodeError:
            logger.warning("Received non json response from erep.lv/battles.json!")
            return get_battle_page()
        __last_battle_update_timestamp = __last_battle_response.get("last_updated", int(dt.timestamp()))
    return __last_battle_response


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # create the background task and run it in the background
        self.last_event_timestamp = timestamp()
        self.bg_task = self.loop.create_task(self.report_battle_events())
        self.bg_rss_task = self.loop.create_task(self.report_rss_events())

    async def on_ready(self):
        logger.info("Client running")
        logger.info("------")

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

                await asyncio.sleep((timestamp() // 300 + 1) * 300 - timestamp())
            except Exception as e:
                logger.error("eRepublik event reader ran into a problem!", exc_info=e)
                try:
                    with open(f"debug/{timestamp()}.rss", "w") as f:
                        f.write(feed_response.text)
                except (NameError, AttributeError):
                    logger.error("There was no Response object!", exc_info=e)
                await asyncio.sleep(10)

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
                    11: discord.Embed(title="Possibly empty **__last-minute__ Air** medals", description=desc)
                }
                for kind, div, data in check_battles(r.get('battles')):
                    if kind == 'epic' and not DB.get_epic(data['div_id']):
                        embed = discord.Embed.from_dict(dict(
                            title=" ".join(data['extra']["intensity_scale"].split("_")).title(),
                            url=data["url"],
                            description=f"Epic battle {' vs '.join(data['sides'])}!\nBattle for {data['region']}, Round {data['zone_id']}",
                            footer=f"Round time {data['round_time']}"
                        ))
                        logger.debug(f"{embed.title=}, {embed.description=}, {embed.url=}, {embed.footer=}")
                        for channel_id in DB.get_kind_notification_channel_ids("epic"):
                            if role_id := DB.get_role_id_for_channel_division(channel_id, division=div):
                                await self.get_channel(channel_id).send(f"<@&{role_id}>", embed=embed)
                            else:
                                await self.get_channel(channel_id).send(embed=embed)
                        DB.add_epic(data['div_id'])

                    if kind == 'empty' and data['round_time_s'] >= 87 * 60:
                        empty_divisions[div].add_field(
                            name=f"**Battle for {data['region']} {' '.join(data['sides'])}**",
                            value=f"[R{data['zone_id']} | Time {data['round_time']}]({data['url']})"
                        )
                for d, e in empty_divisions.items():
                    if e.fields:
                        for channel_id in DB.get_kind_notification_channel_ids("empty"):
                            if role_id := DB.get_role_id_for_channel_division(channel_id, division=d):
                                await self.get_channel(channel_id).send(f"<@&{role_id}>", embed=e)
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
bot = commands.Bot(command_prefix="!")


@bot.event
async def on_ready():
    logger.info("Bot loaded")
    # print(bot.user.name)
    # print(bot.user.id)
    logger.info("------")


@bot.command()
async def unnotify(ctx, kind: str):
    if ctx.author.guild_permissions.administrator:
        channel_id = ctx.channel.id
        if DB.remove_kind_notification_channel(kind, channel_id):
            return await ctx.send(f"I wont notify about {kind} in this channel!")
    return await ctx.send("Nothing to do...")


@bot.command()
async def notify(ctx, kind: str):
    if ctx.author.guild_permissions.administrator:
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        if kind == "epic":
            if DB.add_notification_channel(guild_id, channel_id, kind):
                await ctx.send("I will notify about epics in this channel!")
                await ctx.send(
                    "If You want for me to also add division mentions write:\n"
                    "`!set_division d1 @role_to_mention`\n"
                    "`!set_division d2 @role_to_mention`\n"
                    "`!set_division d3 @role_to_mention`\n"
                    "`!set_division d4 @role_to_mention`\n"
                    "`!set_division air @role_to_mention`"
                )
        elif kind == "events":
            DB.add_notification_channel(guild_id, channel_id, kind)
            await ctx.send("I will notify about eLatvia's events in this channel!")
        elif kind == "empty":
            DB.add_notification_channel(guild_id, channel_id, kind)
            await ctx.send("I will notify about empty medals in this channel!")
        else:
            await ctx.send(f"Unknown {kind=}")
    else:
        return await ctx.send("This command is only available for server administrators")


@bot.command()
async def set_division(ctx, division: str, role_mention):
    if not ctx.author.guild_permissions.administrator:
        return await ctx.send("This command is only available for server administrators")
    if ctx.channel.id not in DB.get_kind_notification_channel_ids("epic"):
        return await ctx.send("This command is only available from registered channels!")
    div_map = dict(D1=1, D2=3, D3=3, D4=4, Air=11)

    if division.title() not in div_map:
        return await ctx.send(f"Unknown {division=}! Available divisions {', '.join(div_map.keys())}")
    for role in ctx.guild.roles:
        if role.mention == role_mention:
            DB.add_role_mapping_entry(ctx.channel.id, div_map[division.title()], role.id)
            return await ctx.send(f"Success! For {division.title()} epics I will mention <@&{role.id}>")
    else:
        await ctx.send(f"Unable to find the role You mentioned...")


@bot.command()
async def exit(ctx):
    if ctx.author.id == ADMIN_ID:
        await ctx.send(f"{ctx.author.mention} Bye!")
        sys.exit(0)
    else:
        return await ctx.send(f"Labs mēģinājums! Mani nogalināt var tikai <@{ADMIN_ID}>")


@bot.command()
async def empty(ctx, division):
    if not ctx.channel.id == 603527159109124096:
        return await ctx.send("Currently unavailable!")
    try:
        div = int(division)
    except ValueError:
        try:
            div = dict(D1=1, D2=3, D3=3, D4=4, Air=11)[division.title()]
        except (AttributeError, KeyError) as e:
            await ctx.send(f"First argument must be a value from: 1, d1, 2, d2, 3, d3, 4, d4, 11, air!")
            return
    s_div = {1: "D1", 2: "D2", 3: "D3", 4: "D4", 11: "Air"}[div]
    embed = discord.Embed(
        title=f"Possibly empty {s_div} medals",
        description=f"'Empty' medals are being guessed based on the division wall. Expect false-positives!",
    )
    for kind, div_div, data in check_battles(get_battle_page().get('battles')):
        if kind == 'empty' and div_div == div:
            embed.add_field(
                name=f"**Battle for {data['region']} {' '.join(data['sides'])}**",
                value=f"[R{data['zone_id']} | Time {data['round_time']}]({data['url']})",
            )
            if len(embed.fields) >= 10:
                return await ctx.send(embed=embed)
    if embed.fields:
        return await ctx.send(embed=embed)
    else:
        return await ctx.send(f"No empty {s_div} medals found")


@empty.error
async def division_error(ctx, error):
    if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
        await ctx.send('Division is mandatory, eg, `!empty [1,2,3,4,11, d1,d2,d3,d4,air, D1,D2,D3,D4,Air] [1-120]`')
    else:
        await ctx.send('Something went wrong! 😔')
        logger.exception(error, exc_info=error)


def main():
    global loop
    logger.info("Starting Bot loop")
    loop.create_task(bot.start(DISCORD_TOKEN))
    logger.info("Starting Client loop")
    loop.create_task(client.start(DISCORD_TOKEN))
    loop.run_forever()


if __name__ == "__main__":
    main()

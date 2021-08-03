import asyncio
import datetime
import json
import logging
import os
import sys
from json import JSONDecodeError
from typing import Union
import time

import pytz
import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
import feedparser

from db import DiscordDB
from map_events import events

APP_NAME = "discord_bot"

os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
load_dotenv()

logger = logging.getLogger(APP_NAME)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

file_logger = logging.FileHandler(f"./logging.log", "w")
file_logger.setLevel(logging.DEBUG)
file_logger.setFormatter(formatter)
logger.addHandler(file_logger)

stream_logger = logging.StreamHandler()
stream_logger.setFormatter(formatter)
logger.addHandler(stream_logger)

os.makedirs("debug", exist_ok=True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_CHANNEL_ID = os.getenv("DEFAULT_CHANNEL_ID", 603527159109124096)
ADMIN_ID = os.getenv("DEFAULT_CHANNEL_ID", 220849530730577920)
DB_NAME = os.getenv("DB_NAME", "discord.db")
DB = DiscordDB(DB_NAME)

UTF_FLAG = {
    1: "🇷🇴",
    9: "🇧🇷",
    10: "🇮🇹",
    11: "🇫🇷",
    12: "🇩🇪",
    13: "🇭🇺",
    14: "🇨🇳",
    15: "🇪🇸",
    23: "🇨🇦",
    24: "🇺🇸",
    26: "🇲🇽",
    27: "🇦🇷",
    28: "🇻🇪",
    29: "🇬🇧",
    30: "🇨🇭",
    31: "🇳🇱",
    32: "🇧🇪",
    33: "🇦🇹",
    34: "🇨🇿",
    35: "🇵🇱",
    36: "🇸🇰",
    37: "🇳🇴",
    38: "🇸🇪",
    39: "🇫🇮",
    40: "🇺🇦",
    41: "🇷🇺",
    42: "🇧🇬",
    43: "🇹🇷",
    44: "🇬🇷",
    45: "🇯🇵",
    47: "🇰🇷",
    48: "🇮🇳",
    49: "🇮🇩",
    50: "🇦🇺",
    51: "🇿🇦",
    52: "🇲🇩",
    53: "🇵🇹",
    54: "🇮🇪",
    55: "🇩🇰",
    56: "🇮🇷",
    57: "🇵🇰",
    58: "🇮🇱",
    59: "🇹🇭",
    61: "🇸🇮",
    63: "🇭🇷",
    64: "🇨🇱",
    65: "🇷🇸",
    66: "🇲🇾",
    67: "🇵🇭",
    68: "🇸🇬",
    69: "🇧🇦",
    70: "🇪🇪",
    71: "🇱🇻",
    72: "🇱🇹",
    73: "🇰🇵",
    74: "🇺🇾",
    75: "🇵🇾",
    76: "🇧🇴",
    77: "🇵🇪",
    78: "🇨🇴",
    79: "🇲🇰",
    80: "🇲🇪",
    81: "🇹🇼",
    82: "🇨🇾",
    83: "🇧🇾",
    84: "🇳🇿",
    164: "🇸🇦",
    165: "🇪🇬",
    166: "🇦🇪",
    167: "🇦🇱",
    168: "🇬🇪",
    169: "🇦🇲",
    170: "🇳🇬",
    171: "🇨🇺",
}
FLAGS = {
    1: "flag_ro",
    9: "flag_br",
    10: "flag_it",
    11: "flag_fr",
    12: "flag_de",
    13: "flag_hu",
    14: "flag_cn",
    15: "flag_es",
    23: "flag_ca",
    24: "flag_us",
    26: "flag_mx",
    27: "flag_ar",
    28: "flag_ve",
    29: "flag_gb",
    30: "flag_ch",
    31: "flag_nl",
    32: "flag_be",
    33: "flag_at",
    34: "flag_cz",
    35: "flag_pl",
    36: "flag_sk",
    37: "flag_no",
    38: "flag_se",
    39: "flag_fi",
    40: "flag_ua",
    41: "flag_ru",
    42: "flag_bg",
    43: "flag_tr",
    44: "flag_gr",
    45: "flag_jp",
    47: "flag_kr",
    48: "flag_in",
    49: "flag_id",
    50: "flag_au",
    51: "flag_za",
    52: "flag_md",
    53: "flag_pt",
    54: "flag_ie",
    55: "flag_de",
    56: "flag_ir",
    57: "flag_pk",
    58: "flag_il",
    59: "flag_th",
    61: "flag_si",
    63: "flag_hr",
    64: "flag_cl",
    65: "flag_rs",
    66: "flag_my",
    67: "flag_ph",
    68: "flag_sg",
    69: "flag_ba",
    70: "flag_ee",
    71: "flag_lv",
    72: "flag_lt",
    73: "flag_kp",
    74: "flag_uy",
    75: "flag_py",
    76: "flag_bo",
    77: "flag_pe",
    78: "flag_co",
    79: "flag_mk",
    80: "flag_me",
    81: "flag_tw",
    82: "flag_cy",
    83: "flag_by",
    84: "flag_nz",
    164: "flag_sa",
    165: "flag_eg",
    166: "flag_ae",
    167: "flag_al",
    168: "flag_ge",
    169: "flag_am",
    170: "flag_ng",
    171: "flag_cu",
}

MENTION_MAPPING = {1: "D1", 2: "D2", 3: "D3", 4: "D4", 11: "Air"}

__last_battle_response = None
__last_battle_update_timestamp = 0


def timestamp_to_datetime(timestamp: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp)


def s_to_human(seconds: Union[int, float]) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds - (h * 3600)) // 60
    s = seconds % 60
    return f"{h:01d}:{m:02d}:{s:02d}"


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
        self.last_event_timestamp = self.timestamp - 43200
        self.bg_task = self.loop.create_task(self.report_epics())
        self.bg_rss_task = self.loop.create_task(self.report_latvian_events())

    @property
    def timestamp(self):
        return int(time.time())

    async def on_ready(self):
        logger.debug("Client running")
        logger.debug("------")

    async def on_error(self, event_method, *args, **kwargs):
        logger.warning(f"Ignoring exception in {event_method}")

    async def report_latvian_events(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                for entry in reversed(feedparser.parse(f"https://www.erepublik.com/en/main/news/military/all/Latvia/0/rss").entries):

                    entry_ts = time.mktime(entry["published_parsed"])
                    if entry_ts > self.last_event_timestamp:
                        msg = entry["summary"]
                        title = ""
                        for kind in events:
                            match = kind.regex.search(msg)
                            if match:
                                text = kind.format.format(**dict(match.groupdict(), **{"current_country": "Latvia"}))
                                title = kind.name
                                break
                        else:
                            has_unknown = True
                            title = "Unable to parse"
                            logger.warning(f"Unable to parse: {str(entry)}")
                            text = msg

                        self.last_event_timestamp = entry_ts
                        entry_datetime = datetime.datetime.fromtimestamp(entry_ts, pytz.timezone("US/Pacific"))
                        embed = discord.Embed(title=title, url=entry["link"], description=text)
                        embed.set_author(name="eLatvia", icon_url="https://www.erepublik.com/images/flags/L/Latvia.gif")
                        embed.set_thumbnail(url="https://www.erepublik.net/images/modules/homepage/logo.png")
                        embed.set_footer(text=f"{entry_datetime.strftime('%F %T')} (eRepublik time)")

                        await self.get_channel(DEFAULT_CHANNEL_ID).send(embed=embed)

                await asyncio.sleep((self.timestamp // 300 + 1) * 300 - self.timestamp)
            except Exception as e:
                logger.error("eRepublik event reader ran into a problem!", exc_info=e)
                try:
                    with open(f"debug/{self.timestamp}.rss", "w") as f:
                        f.write(r.text)
                except NameError:
                    logger.error("There was no Response object!", exc_info=e)
                await asyncio.sleep(10)

    async def report_epics(self):
        await self.wait_until_ready()
        roles = [role for role in self.get_guild(300297668553605131).roles if role.name in MENTION_MAPPING.values()]
        role_mapping = {role.name: role.mention for role in roles}
        while not self.is_closed():
            try:
                r = get_battle_page()
                if not isinstance(r.get("battles"), dict):
                    sleep_seconds = r.get("last_updated") + 60 - self.timestamp
                    await asyncio.sleep(sleep_seconds if sleep_seconds > 0 else 0)
                    continue
                for bid, battle in r.get("battles", {}).items():
                    for div in battle.get("div", {}).values():
                        if div.get("epic") > 1 and not DB.get_epic(div.get("id")):
                            with open(f"debug/{self.timestamp}.json", "w") as f:
                                json.dump(r, f)
                            invader_id = battle["inv"]["id"]
                            defender_id = battle["def"]["id"]
                            embed = discord.Embed(
                                title=" ".join(div.get("intensity_scale").split("_")).title(),
                                url=f"https://www.erepublik.com/en/military/battlefield/{battle['id']}",
                                description=f"Epic battle {UTF_FLAG[invader_id]} vs {UTF_FLAG[defender_id]}!",
                            )
                            embed.set_footer(f"Round time {s_to_human(self.timestamp - battle['start'])}")
                            await self.get_channel(DEFAULT_CHANNEL_ID).send(f"{role_mapping[MENTION_MAPPING[div['div']]]}", embed=embed)
                            DB.add_epic(div.get("id"))

                sleep_seconds = r.get("last_updated") + 60 - self.timestamp
                await asyncio.sleep(sleep_seconds if sleep_seconds > 0 else 0)
            except Exception as e:
                logger.error("Discord bot's eRepublik epic watcher died!", exc_info=e)
                try:
                    with open(f"debug/{self.timestamp}.json", "w") as f:
                        f.write(r.text)
                except NameError:
                    logger.error("There was no Response object!", exc_info=e)
                await asyncio.sleep(10)
        await self.get_channel(DEFAULT_CHANNEL_ID).send(f"<@{ADMIN_ID}> I've stopped, please restart")


loop = asyncio.get_event_loop()
client = MyClient()
bot = commands.Bot(command_prefix="!")


@bot.event
async def on_ready():
    logger.debug("Bot loaded")
    # print(bot.user.name)
    # print(bot.user.id)
    logger.debug("------")


@bot.command()
async def exit(ctx):
    if ctx.author.id == ADMIN_ID:
        await ctx.send(f"{ctx.author.mention} Bye!")
        sys.exit(0)
    else:
        await ctx.send(f"Labs mēģinājums! Mani nogalināt var tikai <@{ADMIN_ID}>")


def main():
    global loop
    loop.create_task(bot.start(DISCORD_TOKEN))
    loop.create_task(client.start(DISCORD_TOKEN))
    loop.run_forever()


if __name__ == "__main__":
    main()

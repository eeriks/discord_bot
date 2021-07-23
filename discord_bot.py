import asyncio
import datetime
import json
import logging
import os
import sys
from json import JSONDecodeError
from typing import Union

import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv

from db import DiscordDB

APP_NAME = "discord_bot"

os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
load_dotenv()
logging.basicConfig(level=logging.WARNING, filename="logging.log", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.DEBUG)
logger.propagate = False
fh = logging.FileHandler(f"./logging.log", "w")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
keep_fds = [fh.stream.fileno()]

os.makedirs("debug", exist_ok=True)

pidfile = "pid"
with open(pidfile, "w") as f:
    f.write(str(os.getpid()))

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_CHANNEL_ID = os.getenv("DEFAULT_CHANNEL_ID", 603527159109124096)
ADMIN_ID = os.getenv("DEFAULT_CHANNEL_ID", 220849530730577920)
DB_NAME = os.getenv("DB_NAME", "discord.db")
DB = DiscordDB(DB_NAME)

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
        self.bg_task = self.loop.create_task(self.report_epics())

    @property
    def timestamp(self):
        return int(datetime.datetime.now().timestamp())

    async def on_ready(self):
        print("Client running")
        print("------")

    async def on_error(self, event_method, *args, **kwargs):
        logger.warning(f"Ignoring exception in {event_method}")

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
                            await self.get_channel(DEFAULT_CHANNEL_ID).send(
                                f"{role_mapping[MENTION_MAPPING[div['div']]]} Epic battle! Round time {s_to_human(self.timestamp - battle['start'])}\n"
                                f"https://www.erepublik.com/en/military/battlefield/{battle['id']}"
                            )
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
    print("Bot loaded")
    # print(bot.user.name)
    # print(bot.user.id)
    print("------")


@bot.command()
async def kill(ctx):
    if ctx.author.id == ADMIN_ID:
        await ctx.send(f"{ctx.author.mention} Bye!")
        sys.exit(1)
    else:
        await ctx.send(f"Labs mēģinājums! Mani nogalināt var tikai <@{ADMIN_ID}>")


def main():
    global loop
    loop.create_task(bot.start(DISCORD_TOKEN))
    loop.create_task(client.start(DISCORD_TOKEN))
    loop.run_forever()


if __name__ == "__main__":
    main()

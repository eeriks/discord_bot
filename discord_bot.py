import asyncio
import datetime
import os
from collections import defaultdict
from json import JSONDecodeError
from typing import Dict, Set

import discord
import pytz
import requests
from discord.ext import commands
from dotenv import load_dotenv

from db import DiscordDB

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DB_NAME = os.getenv('DB_NAME', 'discord.db')
DB = DiscordDB(DB_NAME)

COUNTRIES = {1: 'Romania', 9: 'Brazil', 10: 'Italy', 11: 'France', 12: 'Germany', 13: 'Hungary', 14: 'China',
             15: 'Spain', 23: 'Canada', 24: 'USA', 26: 'Mexico', 27: 'Argentina', 28: 'Venezuela', 29: 'United Kingdom',
             30: 'Switzerland', 31: 'Netherlands', 32: 'Belgium', 33: 'Austria', 34: 'Czech Republic', 35: 'Poland',
             36: 'Slovakia', 37: 'Norway', 38: 'Sweden', 39: 'Finland', 40: 'Ukraine', 41: 'Russia', 42: 'Bulgaria',
             43: 'Turkey', 44: 'Greece', 45: 'Japan', 47: 'South Korea', 48: 'India', 49: 'Indonesia', 50: 'Australia',
             51: 'South Africa', 52: 'Republic of Moldova', 53: 'Portugal', 54: 'Ireland', 55: 'Denmark', 56: 'Iran',
             57: 'Pakistan', 58: 'Israel', 59: 'Thailand', 61: 'Slovenia', 63: 'Croatia', 64: 'Chile', 65: 'Serbia',
             66: 'Malaysia', 67: 'Philippines', 68: 'Singapore', 69: 'Bosnia and Herzegovina', 70: 'Estonia',
             71: 'Latvia', 72: 'Lithuania', 73: 'North Korea', 74: 'Uruguay', 75: 'Paraguay', 76: 'Bolivia', 77: 'Peru',
             78: 'Colombia', 79: 'Republic of Macedonia (FYROM)', 80: 'Montenegro', 81: 'Republic of China (Taiwan)',
             82: 'Cyprus', 83: 'Belarus', 84: 'New Zealand', 164: 'Saudi Arabia', 165: 'Egypt',
             166: 'United Arab Emirates', 167: 'Albania', 168: 'Georgia', 169: 'Armenia', 170: 'Nigeria', 171: 'Cuba'}

FLAGS = {1: 'flag_ro', 9: 'flag_br', 10: 'flag_it', 11: 'flag_fr', 12: 'flag_de', 13: 'flag_hu', 14: 'flag_cn',
         15: 'flag_sp', 23: 'flag_ca', 24: 'flag_us', 26: 'flag_mx', 27: 'flag_ar', 28: 'flag_ve', 29: 'flag_gb',
         30: 'flag_ch', 31: 'flag_nl', 32: 'flag_be', 33: 'flag_at', 34: 'flag_cz', 35: 'flag_pl', 36: 'flag_sk',
         37: 'flag_no', 38: 'flag_se', 39: 'flag_fi', 40: 'flag_ua', 41: 'flag_ru', 42: 'flag_bg', 43: 'flag_tr',
         44: 'flag_gr', 45: 'flag_jp', 47: 'flag_kr', 48: 'flag_in', 49: 'flag_id', 50: 'flag_au', 51: 'flag_za',
         52: 'flag_md', 53: 'flag_pt', 54: 'flag_ie', 55: 'flag_de', 56: 'flag_ir', 57: 'flag_pk', 58: 'flag_il',
         59: 'flag_th', 61: 'flag_si', 63: 'flag_hr', 64: 'flag_cl', 65: 'flag_rs', 66: 'flag_my', 67: 'flag_ph',
         68: 'flag_sg', 69: 'flag_ba', 70: 'flag_ee', 71: 'flag_lv', 72: 'flag_lt', 73: 'flag_kp', 74: 'flag_uy',
         75: 'flag_py', 76: 'flag_bo', 77: 'flag_pe', 78: 'flag_co', 79: 'flag_mk', 80: 'flag_me', 81: 'flag_tw',
         82: 'flag_cy', 83: 'flag_by', 84: 'flag_nz', 164: 'flag_sa', 165: 'flag_eg', 166: 'flag_ae', 167: 'flag_al',
         168: 'flag_ge', 169: 'flag_am', 170: 'flag_ng', 171: 'flag_cu'}


__last_battle_request = None
__last_battle_update_timestamp = 0


def get_battle_page():
    global __last_battle_update_timestamp, __last_battle_request
    if int(datetime.datetime.now().timestamp()) >= __last_battle_update_timestamp + 60:
        r = requests.get('https://www.erepublik.com/en/military/campaignsJson/list').json()
        __last_battle_request = r
        __last_battle_update_timestamp = r.get('last_updated', int(datetime.datetime.now().timestamp()))
    return __last_battle_request


def check_player(player_id: int) -> bool:
    try:
        player_id = int(player_id)
    except ValueError:
        return False
    if not DB.get_player(player_id):
        try:
            r = requests.get(f'https://www.erepublik.com/en/main/citizen-profile-json/{player_id}').json()
        except JSONDecodeError:
            return False
        DB.add_player(player_id, r.get('citizen').get('name'))

    return True


def get_medals(division: int):
    r = get_battle_page()
    if r.get('battles'):
        request_time = timestamp_to_datetime(r.get('last_updated'))
        for battle_id, battle in r.get('battles').items():
            start_time = timestamp_to_datetime(battle.get('start'))
            if start_time < request_time:
                for division_data in battle.get('div', {}).values():
                    if not division_data.get('end') and division_data.get('div') == division:
                        for side, stat in division_data['stats'].items():
                            data = dict(id=battle.get('id'), country_id=battle.get(side).get('id'),
                                        time=request_time - start_time, dmg=0)
                            if stat:
                                data.update(dmg=division_data['stats'][side]['damage'])
                                yield data
                            else:
                                yield data


class MyClient(discord.Client):
    erep_tz = pytz.timezone('US/Pacific')
    hunted: Dict[int, Set[discord.Member]] = defaultdict(set)
    player_mapping: Dict[int, str] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.report_hunted_medals())

    @property
    def timestamp(self):
        return int(datetime.datetime.now().timestamp())

    async def on_ready(self):
        print('Client loaded')
        # print(self.user.name)
        # print(self.user.id)
        print('------')

    async def report_hunted_medals(self):
        await self.wait_until_ready()

        while not self.is_closed():
            r = get_battle_page()
            hunted_ids = DB.get_hunted_player_ids()
            for bid, battle in r.get('battles', {}).items():
                for div in battle.get('div', {}).values():
                    if div['stats'] and not div['end']:
                        for side, side_data in div['stats'].items():
                            if side_data and side_data['citizenId'] in hunted_ids:
                                pid = side_data['citizenId']
                                medal_key = (pid, battle['id'], div['div'], battle[side]['id'], side_data['damage'])
                                if not DB.check_medal(*medal_key):
                                    for member in DB.get_members_to_notify(pid):

                                        format_data = dict(author=member, player=DB.get_player(pid)['name'], battle=bid,
                                                           region=battle.get('region').get('name'),
                                                           division=div['div'], dmg=side_data['damage'],
                                                           side=COUNTRIES[battle[side]['id']])

                                        await self.get_channel(603527159109124096).send(
                                            "<@{author}> **{player}** detected in battle for {region} on {side} side in d{division} with {dmg:,d}dmg\n"
                                            "https://www.erepublik.com/en/military/battlefield/{battle}".format(
                                                **format_data)
                                        )
                                    DB.add_reported_medal(*medal_key)
            sleep_seconds = r.get('last_updated') + 60 - self.timestamp
            await asyncio.sleep(sleep_seconds if sleep_seconds > 0 else 0)


if __name__ == "__main__":
    client = MyClient()
    bot = commands.Bot(command_prefix='!')


    def timestamp_to_datetime(timestamp: int) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(timestamp)


    @bot.event
    async def on_ready():
        print('Bot loaded')
        # print(bot.user.name)
        # print(bot.user.id)
        print('------')


    @bot.command(description="Parādīt lētos d1 BH, kuru dmg ir zem 5m vai Tevis ievadīta vērtībā", help="Lētie d1 BH",
                 category="Cheap medals")
    async def bh1(ctx, max_damage: int = 5_000_000):
        await _send_medal_info(ctx, 1, max_damage)


    @bot.command(description="Parādīt lētos d2 BH, kuru dmg ir zem 10m vai Tevis ievadīta vērtībā", help="Lētie d2 BH",
                 category="Cheap medals")
    async def bh2(ctx, max_damage: int = 10_000_000):
        await _send_medal_info(ctx, 2, max_damage)


    @bot.command(description="Parādīt lētos d3 BH, kuru dmg ir zem 15m vai Tevis ievadīta vērtībā", help="Lētie d3 BH",
                 category="Cheap medals")
    async def bh3(ctx, max_damage: int = 15_000_000):
        await _send_medal_info(ctx, 3, max_damage)


    @bot.command(description="Parādīt lētos d4 BH, kuru dmg ir zem 50m vai Tevis ievadīta vērtībā", help="Lētie d4 BH",
                 category="Cheap medals")
    async def bh4(ctx, max_damage: int = 50_000_000):
        await _send_medal_info(ctx, 4, max_damage)


    @bot.command(description="Parādīt lētos SH, kuru dmg ir zem 50k vai Tevis ievadīta vērtībā", help="Lētie SH",
                 category="Cheap medals")
    async def sh(ctx, min_damage: int = 50000):
        await _send_medal_info(ctx, 11, min_damage)


    @bh1.error
    @bh2.error
    @bh3.error
    @bh4.error
    @sh.error
    async def damage_error(ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send('Damage vērtībai ir jābūt veselam skaitlim')


    async def _send_medal_info(ctx, division: int, damage: int):
        cheap_bhs = []  # Battle id, Side, damage, round time
        for division_data in get_medals(division):
            if division_data['dmg'] < damage:
                division_data['flag'] = FLAGS[division_data['country_id']]
                division_data['country'] = COUNTRIES[division_data['country_id']]
                cheap_bhs.append(division_data)

        if cheap_bhs:
            cheap_bhs = sorted(cheap_bhs, key=lambda _: _['time'])
            cheap_bhs.reverse()
            msg = "\n".join(["{dmg:,d}dmg for :{flag}: {country}, {time} round time "
                             "https://www.erepublik.com/en/military/battlefield/{id}".format(**bh) for bh in cheap_bhs])
            if len(msg) > 2000:
                msg = "\n".join(msg[:2000].split('\n')[:-1])
            await ctx.send(msg)
        else:
            await ctx.send("No medals under {:,d} damage found!".format(damage))


    @bot.command(description="Informēt par spēlētāja mēģinājumiem ņemt medaļas",
                 help="Piereģistrēties uz spēlētāja medaļu paziņošanu", category="Hunting")
    async def hunt(ctx, player_id: int):
        if not check_player(player_id):
            await ctx.send(f"{ctx.author.mention} didn't find any player with `id: {player_id}`!")
        else:
            player_name = DB.get_player(player_id).get('name')
            local_member_id = DB.get_member(ctx.author.id).get('id')
            if DB.add_hunted_player(player_id, local_member_id):
                await ctx.send(f"{ctx.author.mention} You'll be notified for all **{player_name}** medals")
            else:
                await ctx.send(f"{ctx.author.mention} You are already being notified for all **{player_name}** medals")


    @bot.command(description="Beigt informēt par spēlētāja mēģinājumiem ņemt medaļas",
                 help="Atreģistrēties no spēlētāja medaļu paziņošanas", category="Hunting")
    async def remove_hunt(ctx, player_id: int):
        if not check_player(player_id):
            await ctx.send(f"{ctx.author.mention} didn't find any player with `id: {player_id}`!")
        else:
            player_name = DB.get_player(player_id).get('name')
            local_member_id = DB.get_member(ctx.author.id).get('id')
            if DB.remove_hunted_player(player_id, local_member_id):
                await ctx.send(f"{ctx.author.mention} You won't be notified for all **{player_name}** medals")
            else:
                await ctx.send(f"{ctx.author.mention} You weren't being notified for **{player_name}** medals")


    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(DISCORD_TOKEN))
    loop.create_task(client.start(DISCORD_TOKEN))
    loop.run_forever()

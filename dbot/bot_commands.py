import sys

from discord import Embed
from discord.enums import ChannelType
from discord.ext import commands

from dbot.base import ADMIN_ID, DB, DIVISION_MAPPING, MESSAGES, NOTIFICATION_KINDS, logger
from dbot.utils import check_battles, get_battle_page

__all__ = ["bot"]

bot = commands.Bot(command_prefix="!")


def _process_member(member):
    if not DB.get_member(member.id):
        DB.add_member(member.id, str(member))


async def control_register(ctx, *args):
    if " ".join(args) == "From AF With Love!":
        DB.update_member(ctx.author.id, str(ctx.author), True)
        return await ctx.send("✅ You have been registered and are allowed to issue commands privately! 🥳")
    return await ctx.send(MESSAGES["command_failed"])


async def control_notify(ctx, kind):
    if kind == "epic":
        if DB.add_notification_channel(ctx.guild.id, ctx.channel.id, kind):
            return await ctx.send(MESSAGES["notifications_set"].format("epic battles"))
    elif kind == "events":
        if DB.add_notification_channel(ctx.guild.id, ctx.channel.id, kind):
            return await ctx.send(MESSAGES["notifications_set"].format("eLatvia's events"))
    elif kind == "empty":
        if DB.add_notification_channel(ctx.guild.id, ctx.channel.id, kind):
            return await ctx.send(MESSAGES["notifications_set"].format("empty medals"))
    return await ctx.send(MESSAGES["nothing_to_do"])


async def control_unnotify(ctx, kind):
    if DB.remove_kind_notification_channel(kind, ctx.channel.id):
        if kind == "epic":
            return await ctx.send(MESSAGES["notifications_unset"].format("epic battles"))
        if kind == "events":
            return await ctx.send(MESSAGES["notifications_unset"].format("eLatvia's notifications"))
        if kind == "empty":
            return await ctx.send(MESSAGES["notifications_unset"].format("empty medals"))
    return await ctx.send(MESSAGES["command_failed"])


async def control_mention_set(ctx, kind: str, division: str, role: str):
    for guild_role in ctx.guild.roles:
        if guild_role.mention == role:
            if not guild_role.mentionable:
                return await ctx.send(f"❌ Unable to use {role=}, because this role is not globally mentionable!")
            DB.add_role_mapping_entry(kind, ctx.channel.id, DIVISION_MAPPING[division], guild_role.id)
            return await ctx.send(f"✅ Success! For {division} epics I will mention {guild_role.mention}")
    return await ctx.send(MESSAGES["command_failed"])


async def control_mention_remove(ctx, kind: str, division: str):
    if DB.remove_role_mapping(kind, ctx.channel.id, DIVISION_MAPPING[division]):
        return await ctx.send(f"✅ I won't mention here any role about {division} events!")
    return await ctx.send(MESSAGES["nothing_to_do"])


@bot.event
async def on_ready():
    logger.info("Bot loaded")
    # print(bot.user.name)
    # print(bot.user.id)
    logger.info("------")


@bot.command()
async def empty(ctx, division, minutes: int = 0):
    _process_member(ctx.message.author)
    if not (ctx.channel.id == 603527159109124096 or DB.get_member(ctx.message.author.id).get("pm_is_allowed")):
        return await ctx.send("Currently unavailable!")
    try:
        div = int(division)
    except ValueError:
        try:
            div = dict(D1=1, D2=3, D3=3, D4=4, Air=11)[division.title()]
        except (AttributeError, KeyError):
            return await ctx.send("First argument must be a value from: 1, d1, 2, d2, 3, d3, 4, d4, 11, air!")
    s_div = {1: "D1", 2: "D2", 3: "D3", 4: "D4", 11: "Air"}[div]
    embed = Embed(
        title=f"Possibly empty {s_div} medals",
        description="'Empty' medals are being guessed based on the division wall. Expect false-positives!",
    )
    for kind, div_div, data in check_battles(get_battle_page().get("battles")):
        if kind == "empty" and div_div == div and data["round_time_s"] >= minutes * 60:
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
        return await ctx.send("❌ Division is mandatory, eg, `!empty [1,2,3,4,11, d1,d2,d3,d4,air, D1,D2,D3,D4,Air] [1-120]`")
    logger.exception(error, exc_info=error)
    await ctx.send("❌ Something went wrong! 😔")


@bot.command()
async def control(ctx: commands.Context, command: str, *args):
    _process_member(ctx.message.author)
    if command == "register":
        return await control_register(ctx, *args)
    if command in ["notify", "unnotify"]:
        if ctx.channel.type == ChannelType.private:
            return await ctx.send(MESSAGES["not_in_pm"])
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send(MESSAGES["not_admin"])
        if not args:
            return await ctx.send(
                f"❌ Please provide what kind of notifications You would like to {'en' if command == 'notify' else 'dis'}able! Currently available: {', '.join(NOTIFICATION_KINDS)}"
            )
        kind = str(args[0]).lower()
        if kind not in NOTIFICATION_KINDS:
            return await ctx.send(f'❌ Notification {kind=} is unknown! Currently available: {", ".join(NOTIFICATION_KINDS)}')
        if command == "notify":
            return await control_notify(ctx, kind)
        if command == "unnotify":
            return await control_unnotify(ctx, kind)

    if command == "mention":
        if ctx.channel.type == ChannelType.private:
            return await ctx.send(MESSAGES["not_in_pm"])
        if not ctx.author.guild_permissions.administrator:
            return await ctx.send(MESSAGES["not_admin"])
        if not args or not 3 <= len(args) <= 4:
            return await ctx.send(MESSAGES["mention_help"].format(command=command))

        try:
            kind, action, division, *role = args
            if role:
                role = role[0]
            kind = str(kind).lower()
            if ctx.channel.id not in DB.get_kind_notification_channel_ids(kind):
                return await ctx.send(MESSAGES["only_registered_channels"])
            if kind not in ("epic", "empty"):
                return await ctx.send(f"❌ {kind=} doesn't support division mentioning!")

            if action not in ("set", "remove"):
                return await ctx.send(MESSAGES["mention_help"].format(command=command))
            action = str(action).lower()
            division = str(division).title()
            if division not in DIVISION_MAPPING:
                await ctx.send(f"❌ Unknown {division=}! Available divisions: {', '.join(d.title() for d in DIVISION_MAPPING.keys())}")
                return await ctx.send(MESSAGES["mention_info"].format(kind=kind))

            if action == "set":
                return await control_mention_set(ctx, kind, division, role)
            if action == "remove":
                return await control_mention_remove(ctx, kind, division)
        except Exception as e:
            logger.warning(str(e), exc_info=e, stacklevel=3)
            return await ctx.send(MESSAGES["mention_help"].format(command=command))

    if command == "exit":
        if ctx.author.id == ADMIN_ID:
            await ctx.send(f"{ctx.author.mention} Bye!")
            sys.exit(0)
    return await ctx.send(f"❌ Unknown {command=}!")


@empty.error
async def control_error(ctx, error):
    logger.exception(error, exc_info=error)
    return await ctx.send(MESSAGES["command_failed"])


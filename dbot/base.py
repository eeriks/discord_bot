import logging
import os
import sys

from db import DiscordDB

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


MENTION_MAPPING = {1: "D1", 2: "D2", 3: "D3", 4: "D4", 11: "Air"}
DIVISION_MAPPING = {v: k for k, v in MENTION_MAPPING.items()}

NOTIFICATION_KINDS = (
    "epic",
    "events",
    "empty",
)

MESSAGES = dict(
    not_admin="❌ Only server administrators are allowed to enable notifications!",
    not_in_pm="❌ Unable to notify in PMs!",
    command_failed="❌ Command failed!",
    only_registered_channels="❌ This command is only available from registered channels!",
    mention_help="❌ Please provide kind, action, division and role to mention! Eg. '{command} epic set d4 @div4' or '{command} empty remove d3'",
    mention_info="ℹ️ If You want for me to also add division mentions write:\n`!control mention [kind] set [division] [role_mention]`\n"
    "Example: `!control mention {kind} set d4 @div4` or `!control mention {kind} set air @aviators`",
    nothing_to_do="ℹ️ Nothing to do here...",
    notifications_unset="✅ I won't notify about {} in this channel!",
    notifications_set="✅ I will notify about {} in this channel!",
)

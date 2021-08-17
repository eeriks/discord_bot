from typing import Dict, Optional, Union, List, Tuple
import logging
from sqlite_utils import Database
from sqlite_utils.db import NotFoundError

logger = logging.getLogger(__name__)


class DiscordDB:
    _name: str
    _db: Database

    def __init__(self, db_name: str = ""):
        self._name = db_name
        if not self._name:
            self._db = Database(memory=True)
        else:
            self._db = Database(self._name)
        if "member" not in self._db.table_names():
            self._db.create_table("member", {"id": int, "name": str}, pk="id", not_null={"id", "name"})

        if "player" not in self._db.table_names():
            self._db.create_table("player", {"id": int, "name": str}, pk="id", not_null={"id", "name"})

        if "epic" not in self._db.table_names():
            self._db.create_table("epic", {"id": int, "fake": bool}, pk="id", not_null={"id"}, defaults={"fake": False})

        if "rss_feed" not in self._db.table_names():
            self._db.create_table("rss_feed", {"id": int, "timestamp": float}, pk="id", not_null={"id", "timestamp"})

        if "notification_channel" not in self._db.table_names():
            self._db.create_table(
                "notification_channel", {"id": int, "guild_id": int, "channel_id": int, "kind": str}, pk="id", not_null={"id", "guild_id", "channel_id"}, defaults={"kind": "epic"}
            )
            self._db["notification_channel"].create_index(("guild_id", "channel_id", "kind"), unique=True)
            self._db.create_table("role_mapping", {"id": int, "channel_id": int, "division": int, "role_id": int}, pk="id", not_null={"id", "channel_id", "division", "role_id"})
            self._db["role_mapping"].add_foreign_key("channel_id", "notification_channel", "channel_id")
            self._db["role_mapping"].create_index(("channel_id", "division"), unique=True)

        self._db.vacuum()

        self.member = self._db.table("member")
        self.player = self._db.table("player")
        self.epic = self._db.table("epic")
        self.rss_feed = self._db.table("rss_feed")
        self.channel = self._db.table("notification_channel")
        self.role_mapping = self._db.table("role_mapping")

    # Player methods

    def get_player(self, pid: int) -> Optional[Dict[str, Union[int, str]]]:
        """Get Player

        :param pid: int Player ID
        :return: player id, name if player exists
        """
        try:
            return self.player.get(pid)
        except NotFoundError:
            return None

    def add_player(self, pid: int, name: str) -> bool:
        """Add player.

        :param pid: int Player ID
        :param name: Player Name
        :return: bool Player added
        """
        if not self.get_player(pid):
            self.player.insert({"id": pid, "name": name})
            return True
        else:
            return False

    def update_player(self, pid: int, name: str) -> bool:
        """Update player"s record

        :param pid: int Player ID
        :param name: Player Name
        :return: bool
        """
        if self.get_player(pid):
            self.player.update(pid, {"name": name})
            return True
        else:
            return False

    # Member methods

    def get_member(self, member_id) -> Dict[str, Union[int, str]]:
        """Get discord member

        :param member_id: int Discord Member ID
        :type member_id: int
        :return: local id, name, mention number if discord member exists else None
        :rtype: Union[Dict[str, Union[int, str]], None]
        """
        try:
            return self.member.get(member_id)
        except NotFoundError:
            raise NotFoundError("Member with given id not found")

    def add_member(self, id: int, name: str) -> Dict[str, Union[int, str]]:
        """Add discord member.

        :param id: int Discord member ID
        :param name: Discord member Name
        """
        try:
            self.member.insert({"id": id, "name": name})
        finally:
            return self.member.get(id)

    def update_member(self, member_id: int, name: str) -> bool:
        """Update discord member"s record

        :param member_id: Discord Mention ID
        :type member_id: int Discord Mention ID
        :param name: Discord user name
        :type name: str Discord user name
        :return: bool
        """
        try:
            member = self.get_member(member_id)
        except NotFoundError:
            member = self.add_member(member_id, name)
        self.member.update(member["id"], {"name": name})
        return True

    # Epic Methods

    def get_epic(self, division_id: int) -> Optional[Dict[str, Union[int, str]]]:
        """Get Epic division

        :param division_id: int Division ID
        :return: division id
        """
        try:
            return self.epic.get(division_id)
        except NotFoundError:
            return None

    def add_epic(self, division_id: int) -> bool:
        """Add Epic division.

        :param division_id: int Epic division ID
        :return: bool Epic division added
        """
        if not self.get_epic(division_id):
            self.epic.insert({"id": division_id})
            return True
        return False

    # RSS Event Methods

    def get_rss_feed_timestamp(self, country_id: int) -> float:
        """Get latest processed RSS Feed event's timestamp for country

        :param country_id: int Country ID
        :return: timestamp
        """
        try:
            return self.rss_feed.get(country_id)["timestamp"]
        except NotFoundError:
            return 0

    def set_rss_feed_timestamp(self, country_id: int, timestamp: float) -> None:
        """Set latest processed RSS Feed event's timestamp for country

        :param country_id: int Country ID
        :param timestamp: float UNIX timestamp
        """
        if self.get_rss_feed_timestamp(country_id):
            self.rss_feed.update(country_id, {"timestamp": timestamp})
        else:
            self.rss_feed.insert({"id": country_id, "timestamp": timestamp})

    # RSS Event Methods

    def add_notification_channel(self, guild_id: int, channel_id: int, kind: str) -> bool:
        if channel_id in self.get_kind_notification_channel_ids(kind):
            return False
        self.channel.insert({"guild_id": guild_id, "channel_id": channel_id, "kind": kind})
        return True

    def get_kind_notification_channel_ids(self, kind: str) -> List[int]:
        channels = [row["channel_id"] for row in self.channel.rows_where("kind = ?", [kind])]
        logger.info(f"Found {len(channels)} channels for {kind} kind: {channels}")
        return channels

    def remove_kind_notification_channel(self, kind, channel_id) -> bool:
        if channel_id in self.get_kind_notification_channel_ids(kind):
            logger.warning(f"removing channel with id {channel_id}")
            self.channel.delete_where("kind = ? and channel_id = ?", (kind, channel_id))
            self.remove_role_mappings(channel_id)
            return True
        return False

    def remove_role_mappings(self, channel_id: int):
        return self.role_mapping.delete_where("channel_id = ?", (channel_id, ))

    def add_role_mapping_entry(self, channel_id: int, division: int, role_id: int) -> bool:
        if division not in (1, 2, 3, 4, 11):
            return False
        try:
            row = next(self.role_mapping.rows_where("channel_id = ? and division = ?", [channel_id, division]))
            self.role_mapping.update(row["id"], {"channel_id": channel_id, "division": division, "role_id": role_id})
        except StopIteration:
            self.role_mapping.insert({"channel_id": channel_id, "division": division, "role_id": role_id})
        return True

    def get_role_id_for_channel_division(self, channel_id: int, division: int) -> Optional[int]:
        rows = self.role_mapping.rows_where('channel_id = ? and division = ?', (channel_id, division))
        for row in rows:
            return row['role_id']


import logging
from typing import Dict, List, Optional, Union

from sqlite_utils import Database
from sqlite_utils.db import NotFoundError


class DiscordDB:
    _name: str
    _db: Database

    def __init__(self, db_name: str = ""):
        self._db = Database(db_name) if db_name else Database(memory=True)

        self.initialize()

        self.member = self._db.table("member")
        self.player = self._db.table("player")
        self.division = self._db.table("division")
        self.rss_feed = self._db.table("rss_feed")
        self.channel = self._db.table("channel")
        self.role_mapping = self._db.table("role_mapping")

    def initialize(self):
        hard_tables = ["member", "player", "channel", "role_mapping"]
        db_tables = self._db.table_names()
        if "member" not in db_tables:
            self._db.create_table("member", {"name": str, "pm_is_allowed": bool}, pk="id", not_null={"name", "pm_is_allowed"}, defaults={"pm_is_allowed": False})
        else:
            self._db.create_table("member_tmp", {"name": str, "pm_is_allowed": bool}, pk="id", not_null={"name", "pm_is_allowed"}, defaults={"pm_is_allowed": False})
            for row in self._db.table("member").rows:
                self._db["member_tmp"].insert(row)
                logging.info(f"Moving row {row} to tmp member table")
            self._db["member"].drop(True)
            self._db.create_table("member", {"name": str, "pm_is_allowed": bool}, pk="id", not_null={"name", "pm_is_allowed"}, defaults={"pm_is_allowed": False})
            for row in self._db.table("member_tmp").rows:
                self._db["member"].insert(row)
                logging.info(f"Moving row {row} from tmp member table")
            self._db["member_tmp"].drop(True)

        if "player" not in db_tables:
            self._db.create_table("player", {"name": str}, pk="id", not_null={"name"})
        if "notification_channel" in db_tables or "channel" not in db_tables:
            try:
                self._db.create_table("channel", {"guild_id": int, "channel_id": int, "kind": str}, pk="id", not_null={"guild_id", "channel_id", "kind"}, defaults={"kind": "epic"})
                self._db["channel"].create_index(("guild_id", "channel_id", "kind"), unique=True)
            except:
                pass
            for row in self._db.table("notification_channel").rows:
                self._db["channel"].insert(row)
        if "role_mapping" not in db_tables:
            self._db.create_table("role_mapping", {"channel_id": int, "division": int, "role_id": int}, pk="id", not_null={"channel_id", "division", "role_id"})
            self._db["role_mapping"].add_foreign_key("channel_id", "channel", "id")
            self._db["role_mapping"].create_index(("channel_id", "division"), unique=True)

        for table in self._db.table_names():
            if table not in hard_tables:
                self._db.table(table).drop(ignore=True)

        self._db.create_table("division", {"division_id": int, "epic": bool, "empty": bool}, pk="id", defaults={"epic": False, "empty": False}, not_null={"division_id"})
        self._db.create_table("rss_feed", {"timestamp": float}, pk="id", not_null={"timestamp"})

        self._db.vacuum()

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
            return {}

    def add_member(self, id: int, name: str, pm_is_allowed: bool = False) -> Dict[str, Union[int, str]]:
        """Add discord member.

        :param id: int Discord member ID
        :param name: Discord member Name
        :param pm_is_allowed: Allow discord member to contact bot through PMs
        """
        try:
            self.member.insert({"id": id, "name": name, "pm_is_allowed": pm_is_allowed})
        finally:
            return self.member.get(id)

    def update_member(self, member_id: int, name: str, pm_is_allowed: bool = None) -> bool:
        """Update discord member"s record

        :param member_id: Discord Mention ID
        :type member_id: int
        :param name: Discord user name
        :type name: str
        :param pm_is_allowed: Is discord user allowed to interact through PMs
        :type pm_is_allowed: Optional[bool]
        :return: bool
        """
        member = self.get_member(member_id)
        if member:
            if pm_is_allowed is None:
                pm_is_allowed = self.member.get(member_id).get("pm_is_allowed")
            self.member.update(member["id"], {"name": name, "pm_is_allowed": pm_is_allowed})
            return True
        self.add_member(member_id, name)
        return True

    # Epic Methods

    def check_epic(self, division_id: int) -> bool:
        """Check if epic has been registered in the division

        :param division_id: int Division ID
        :return: bool
        """
        try:
            return bool(next(self.division.rows_where("division_id = ? and epic = ?", (division_id, True))))
        except StopIteration:
            return False

    def add_epic(self, division_id: int) -> bool:
        """Register epic in division.

        :param division_id: int Epic division ID
        :return: bool Epic division added
        """
        if not self.check_epic(division_id):
            self.division.insert({"division_id": division_id, "epic": True})
            return True
        return False

    # Epic Methods

    def check_empty_medal(self, division_id: int) -> bool:
        """Get Epic division

        :param division_id: int Division ID
        :return: division id
        """
        try:
            return bool(next(self.division.rows_where("division_id = ? and empty = ?", (division_id, True))))
        except StopIteration:
            return False

    def add_empty_medal(self, division_id: int) -> bool:
        """Add Epic division.

        :param division_id: int Epic division ID
        :return: bool Epic division added
        """
        if not self.check_empty_medal(division_id):
            self.division.insert({"division_id": division_id, "empty": True})
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

    # Notification methods

    def add_notification_channel(self, guild_id: int, channel_id: int, kind: str) -> bool:
        if channel_id in self.get_kind_notification_channel_ids(kind):
            return False
        self.channel.insert({"guild_id": guild_id, "channel_id": channel_id, "kind": kind})
        return True

    def get_kind_notification_channel_ids(self, kind: str) -> List[int]:
        channels = [row["channel_id"] for row in self.channel.rows_where("kind = ?", [kind])]
        return channels

    def get_notification_channel_id(self, kind: str, *, guild_id: int = None, channel_id: int = None) -> Optional[int]:
        if guild_id is None and channel_id is None:
            raise RuntimeError("Must provide either guild_id or channel_id!")
        for row in self.channel.rows_where(f"kind = ? and {'guild_id' if guild_id is not None else 'channel_id'} = ?", [kind, guild_id or channel_id]):
            return row["id"]

    def remove_kind_notification_channel(self, kind, channel_id) -> bool:
        if channel_id in self.get_kind_notification_channel_ids(kind):
            self.remove_all_channel_role_mappings(channel_id, kind)
            self.channel.delete_where("kind = ? and channel_id = ?", (kind, channel_id))
            return True
        return False

    # Role mapping methods

    def add_role_mapping_entry(self, kind: str, channel_id: int, division: int, role_id: int) -> bool:
        ch_id = self.get_notification_channel_id(kind, channel_id=channel_id)
        if division not in (1, 2, 3, 4, 11):
            return False
        try:
            row = next(self.role_mapping.rows_where("channel_id = ? and division = ?", [ch_id, division]))
            self.role_mapping.update(row["id"], {"channel_id": ch_id, "division": division, "role_id": role_id})
        except StopIteration:
            self.role_mapping.insert({"channel_id": ch_id, "division": division, "role_id": role_id})
        return True

    def remove_all_channel_role_mappings(self, channel_id: int, kind: str):
        ch_id = self.get_notification_channel_id(kind, channel_id=channel_id)
        for d in (1, 2, 3, 4, 11):
            self.remove_role_mapping(kind, ch_id, d)

    def remove_role_mapping(self, kind: str, channel_id: int, division_id: int) -> bool:
        try:
            ch_id = self.get_notification_channel_id(kind, channel_id=channel_id)
            row = next(self.role_mapping.rows_where("channel_id = ? and division = ? ", (ch_id, division_id)))
            self.role_mapping.delete(row["id"])
            return True
        except StopIteration:
            return False

    def get_role_id_for_channel_division(self, *, kind: str, channel_id: int, division: int) -> Optional[int]:
        ch_id = self.get_notification_channel_id(kind, channel_id=channel_id)
        rows = self.role_mapping.rows_where("channel_id = ? and division = ?", (ch_id, division))
        for row in rows:
            return row["role_id"]

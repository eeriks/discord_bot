from typing import Dict, Optional, Union

from sqlite_utils import Database
from sqlite_utils.db import NotFoundError


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

        self._db.vacuum()

        self.member = self._db.table("member")
        self.player = self._db.table("player")
        self.epic = self._db.table("epic")

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

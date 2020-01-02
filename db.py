from typing import List, Union, Dict

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
            self._db.create_table("member", {"id": int, "name": str, "mention_number": int},
                                  pk="id", not_null={"id", "name", "mention_number"})

        if "player" not in self._db.table_names():
            self._db.create_table("player", {"id": int, "name": str}, pk="id", not_null={"id", "name"})

        if "hunted" not in self._db.table_names():
            self._db.create_table("hunted", {"id": int, "member_id": int, "player_id": int},
                                  pk="id", not_null={"id", "member_id", "player_id"})
            self._db['hunted'].create_index(["member_id", "player_id"], unique=True)

        if "medals" not in self._db.table_names():
            self._db.create_table("medals",
                                  dict(id=int, player_id=int, battle_id=int, division_id=int, side_id=int, damage=int),
                                  not_null={"id", "player_id", "battle_id", "division_id", "side_id", "damage"},
                                  pk="id", defaults={"damage": 0})
            self._db['medals'].create_index(["player_id", "battle_id", "division_id", "side_id"], unique=True)

        if "hunted_players" not in self._db.view_names():
            self._db.create_view("hunted_players", "select distinct player_id from hunted")

        self._db.add_foreign_keys([("hunted", "member_id", "member", "id"),
                                   ("hunted", "player_id", "player", "id"),
                                   ("medals", "player_id", "player", "id")])
        self._db.vacuum()

        self.member = self._db.table("member")
        self.player = self._db.table("player")
        self.hunted = self._db.table("hunted")
        self.medals = self._db.table("medals")
        self.hunted_players = self._db.table("hunted_players")

    # Player methods

    def get_player(self, pid: int) -> Union[Dict[str, Union[int, str]], None]:
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

    def get_member(self, mention_number: int = None, local_id: int = None) -> Dict[str, Union[int, str]]:
        """Get discord member

        :param mention_number: int Discord Member ID
        :type mention_number: int
        :param local_id: Query user by local id
        :type local_id: int
        :return: local id, name, mention number if discord member exists else None
        :rtype: Union[Dict[str, Union[int, str]], None]
        """
        if local_id:
            return self.member.get(local_id)
        elif mention_number:
            try:
                return next(self.member.rows_where("mention_number = ?", [mention_number]))
            except StopIteration:
                raise NotFoundError("Member with given kwargs not found")
        else:
            raise NotFoundError("mention_number or local_id must be provided!")

    def add_member(self, mention_number: int, name: str) -> int:
        """Add discord member.

        :param mention_number: int Discord member ID
        :param name: Discord member Name
        """
        return self.member.insert({"mention_number": mention_number, "name": name}).last_pk

    def update_member(self, local_id: int, name: str = "", mention_number: int = None) -> bool:
        """Update discord member"s record

        :param mention_number: Discord Mention ID
        :type mention_number: int Discord Mention ID
        :param name: Discord user name
        :type name: str Discord user name
        :param local_id: Local id of Discord mention ID
        :type local_id: int
        :return: bool
        """
        member = self.get_member(local_id=local_id)
        if member and (name or mention_number):
            if name and not mention_number:
                self.member.update(member["id"], {"name": name})
            elif mention_number and not name:
                self.member.update(member["id"], {"mention_number": mention_number})
            else:
                self.member.update(member["id"], {"name": name, "mention_number": mention_number})
            return True
        else:
            return False

    def check_medal(self, pid: int, bid: int, div: int, side: int, dmg: int) -> bool:
        """Check if players (pid) damage (dmg) in battle (bid) for side in division (div) has been registered

        :param pid: Player ID
        :type pid: int
        :param bid: Battle ID
        :type bid: int
        :param div: Division
        :type div: int
        :param side: Side ID
        :type side: int
        :param dmg: Damage amount
        :type dmg: int
        :return: If medal has been registered
        :rtype: bool
        """
        medals = self.medals
        record_pk = medals.lookup(dict(player_id=pid, battle_id=bid, division_id=div, side_id=side))
        return medals.get(record_pk)["damage"] == dmg

    def add_reported_medal(self, pid: int, bid: int, div: int, side: int, dmg: int):
        medals = self.medals
        pk = medals.lookup(dict(player_id=pid, battle_id=bid, division_id=div, side_id=side))
        medals.update(pk, {"damage": dmg})
        return True

    def delete_medals(self, bid: List[int]):
        self.medals.delete_where("battle_id in (%s)" % "?" * len(bid), bid)
        return True

    def check_hunt(self, pid: int, member_id: int) -> bool:
        try:
            next(self.hunted.rows_where("player_id=? and member_id=?", [pid, member_id]))
            return True
        except StopIteration:
            return False

    def add_hunted_player(self, pid: int, member_id: int) -> bool:
        if self.check_hunt(pid, member_id):
            return False
        else:
            self.hunted.insert({"player_id": pid, "member_id": member_id})
            return True

    def remove_hunted_player(self, pid: int, member_id: int) -> bool:
        if self.check_hunt(pid, member_id):
            self.hunted.delete_where("player_id=? and member_id=?", (pid, member_id))
            return True
        else:
            return False

    def get_hunted_player_ids(self) -> List[int]:
        return [r["player_id"] for r in self.hunted_players.rows]

    def get_members_to_notify(self, pid: int) -> List[int]:
        members = []
        for row in self.hunted.rows_where("player_id = ?", [pid]):
            member = self.get_member(local_id=row["member_id"])
            members.append(member["mention_number"])
        return members

import unittest

from sqlite_utils.db import NotFoundError

from db import DiscordDB


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = DiscordDB()

    def test_member(self):
        member = {'id': 1200, 'name': 'username'}
        self.db.add_member(**member)
        self.assertEqual(self.db.add_member(**member), member)

        self.assertRaises(NotFoundError, self.db.get_member, member_id=100)
        self.assertEqual(self.db.get_member(member_id=member['id']), member)

        member.update(name="Success")
        self.assertTrue(self.db.update_member(member['id'], member['name']))
        self.assertEqual(self.db.get_member(member_id=member['id']), member)

    def test_player(self):
        player = {'id': 1, 'name': 'plato'}
        self.assertTrue(self.db.add_player(player['id'], player['name']))
        self.assertFalse(self.db.add_player(player['id'], player['name']))
        self.assertEqual(self.db.get_player(0), None)
        self.assertEqual(self.db.get_player(player['id']), player)

        self.assertFalse(self.db.update_player(0, "Error"))
        player["name"] = "New name"
        self.assertTrue(self.db.update_player(player["id"], player["name"]))
        self.assertEqual(self.db.get_player(player['id']), player)

    def test_medal(self):
        kwargs = {"pid": 1, "bid": 235837, "div": 4, "side": 71, "dmg": 1}
        self.assertFalse(self.db.check_medal(**kwargs))
        self.assertTrue(self.db.add_reported_medal(**kwargs))
        self.assertTrue(self.db.check_medal(**kwargs))
        self.assertTrue(self.db.delete_medals([kwargs['bid']]))

    def test_hunt(self):
        member_1 = self.db.add_member(2, name="one")
        member_2 = self.db.add_member(3, name="two")
        member_3 = self.db.add_member(4, name="three")
        self.db.add_player(1, 'plato')
        self.db.add_player(2, 'draco')
        self.assertFalse(self.db.check_hunt(1, member_1['id']))
        self.assertFalse(self.db.remove_hunted_player(1, member_1['id']))
        player_1_hunt = [{'id': 1, "member_id": member_1['id'], 'player_id': 1, 'channel_id': 123},
                         {'id': 2, "member_id": member_2['id'], 'player_id': 1, 'channel_id': 234},
                         {'id': 3, "member_id": member_3['id'], 'player_id': 1, 'channel_id': 345}]
        for hunt in player_1_hunt:
            self.assertTrue(self.db.add_hunted_player(hunt['player_id'], hunt['member_id'], hunt['channel_id']))

        player_2_hunt = [{'id': 4, "member_id": member_1['id'], 'player_id': 2, 'channel_id': 456}]
        for hunt in player_2_hunt:
            self.assertTrue(self.db.add_hunted_player(hunt['player_id'], hunt['member_id'], hunt['channel_id']))

        self.assertListEqual(self.db.get_hunted_player_ids(), [1, 2])
        self.assertListEqual(self.db.get_members_to_notify(1), player_1_hunt)
        self.assertListEqual(self.db.get_members_to_notify(2), player_2_hunt)

        self.assertFalse(self.db.add_hunted_player(1, member_1['id'], 567))
        self.assertTrue(self.db.check_hunt(1, member_1['id']))
        self.assertTrue(self.db.remove_hunted_player(1, member_1['id']))
        self.assertFalse(self.db.check_hunt(1, member_1['id']))

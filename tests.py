import unittest

from sqlite_utils.db import NotFoundError

from db import DiscordDB


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = DiscordDB()

    def test_member(self):
        member = {'mention_number': 1, 'name': 'username'}
        member.update(id=self.db.add_member(**member))
        self.assertRaises(NotFoundError, self.db.get_member)
        self.assertRaises(NotFoundError, self.db.get_member, mention_number=100)
        self.assertEqual(self.db.get_member(local_id=member['id']), member)
        self.assertEqual(self.db.get_member(mention_number=member['mention_number']), member)
        self.assertFalse(self.db.update_member(member['id']))
        member.update(name="Success", mention_number=2)
        self.assertTrue(self.db.update_member(member['id'], name=member['name'],
                                              mention_number=member['mention_number']))
        self.assertTrue(self.db.update_member(member['id'], name=member['name']))
        self.assertTrue(self.db.update_member(member['id'], mention_number=member['mention_number']))
        self.assertEqual(self.db.get_member(local_id=member['id']), member)
        self.assertEqual(self.db.get_member(mention_number=member['mention_number']), member)

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
        member_id = self.db.add_member(mention_number=2, name="username")
        member_id2 = self.db.add_member(mention_number=3, name="username")
        member_id3 = self.db.add_member(mention_number=4, name="username")
        self.db.add_player(1, 'plato')
        self.db.add_player(2, 'draco')
        self.assertFalse(self.db.check_hunt(1, member_id))
        self.assertFalse(self.db.remove_hunted_player(1, member_id))
        self.assertTrue(self.db.add_hunted_player(1, member_id))
        self.assertTrue(self.db.add_hunted_player(1, member_id2))
        self.assertTrue(self.db.add_hunted_player(1, member_id3))
        self.assertTrue(self.db.add_hunted_player(2, member_id))
        self.assertListEqual(self.db.get_hunted_player_ids(), [1, 2])
        self.assertListEqual(self.db.get_members_to_notify(1), [2, 3, 4])
        self.assertListEqual(self.db.get_members_to_notify(2), [2])
        self.assertFalse(self.db.add_hunted_player(1, member_id))
        self.assertTrue(self.db.check_hunt(1, member_id))
        self.assertTrue(self.db.remove_hunted_player(1, member_id))
import unittest
import re

from sqlite_utils.db import NotFoundError

from dbot import constants, db


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = db.DiscordDB()

    def test_member(self):
        member = {"id": 1200, "name": "username"}
        self.db.add_member(**member)
        self.assertEqual(self.db.add_member(**member), member)

        self.assertRaises(NotFoundError, self.db.get_member, member_id=100)
        self.assertEqual(self.db.get_member(member_id=member["id"]), member)

        member.update(name="Success")
        self.assertTrue(self.db.update_member(member["id"], member["name"]))
        self.assertEqual(self.db.get_member(member_id=member["id"]), member)

    def test_player(self):
        player = {"id": 1, "name": "plato"}
        self.assertTrue(self.db.add_player(player["id"], player["name"]))
        self.assertFalse(self.db.add_player(player["id"], player["name"]))
        self.assertEqual(self.db.get_player(0), None)
        self.assertEqual(self.db.get_player(player["id"]), player)

        self.assertFalse(self.db.update_player(0, "Error"))
        player["name"] = "New name"
        self.assertTrue(self.db.update_player(player["id"], player["name"]))
        self.assertEqual(self.db.get_player(player["id"]), player)

    def test_epic(self):
        self.assertFalse(self.db.get_epic(123456))
        self.assertTrue(self.db.add_epic(123456))
        self.assertFalse(self.db.add_epic(123456))
        self.assertTrue(self.db.get_epic(123456))

    def test_rss_feed(self):
        self.assertEqual(self.db.get_rss_feed_timestamp(71), 0.0)
        self.db.set_rss_feed_timestamp(71, 16000000)
        self.assertEqual(self.db.get_rss_feed_timestamp(71), 16000000.0)


class TestRegexes(unittest.TestCase):
    def test_events(self):
        for event in constants.events:
            self.assertTrue(isinstance(event, constants.EventKind))
            self.assertTrue(event.slug)
            self.assertTrue(event.name)
            self.assertTrue(isinstance(event.regex, re.Pattern))
            self.assertTrue(event.format)


if __name__ == '__main__':
    unittest.main()

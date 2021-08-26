import re
import unittest

from dbot import constants, db


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = db.DiscordDB()

    def test_member(self):
        member = {"id": 1200, "name": "username", "pm_is_allowed": False}
        self.assertTrue(self.db.add_member(**member))
        self.assertEqual(self.db.add_member(**member), member)

        self.assertFalse(self.db.get_member(100))
        self.assertEqual(self.db.get_member(member_id=member["id"]), member)

        member.update(name="Success")
        self.assertTrue(self.db.update_member(member["id"], member["name"]))
        self.assertEqual(self.db.get_member(member_id=member["id"]), member)
        self.assertTrue(self.db.update_member(100, member["name"]))

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
        self.assertFalse(self.db.check_epic(123456))
        self.assertTrue(self.db.add_epic(123456))
        self.assertFalse(self.db.add_epic(123456))
        self.assertTrue(self.db.check_epic(123456))

    def test_empty(self):
        self.assertFalse(self.db.check_empty_medal(123456))
        self.assertTrue(self.db.add_empty_medal(123456))
        self.assertFalse(self.db.add_empty_medal(123456))
        self.assertTrue(self.db.check_empty_medal(123456))

    def test_rss_feed(self):
        self.assertEqual(self.db.get_rss_feed_timestamp(71), 0.0)
        self.db.set_rss_feed_timestamp(71, 16000000)
        self.assertEqual(self.db.get_rss_feed_timestamp(71), 16000000.0)
        self.db.set_rss_feed_timestamp(71, 16000001)
        self.assertEqual(self.db.get_rss_feed_timestamp(71), 16000001.0)

    def test_channels(self):
        kind = "epic"
        self.assertTrue(self.db.add_notification_channel(13, 16, kind))
        self.assertFalse(self.db.add_notification_channel(13, 16, kind))
        self.assertListEqual(self.db.get_kind_notification_channel_ids(kind), [16])
        self.assertFalse(self.db.add_role_mapping_entry(kind, 16, 5, 160003))
        self.assertTrue(self.db.add_role_mapping_entry(kind, 16, 3, 160003))
        self.assertTrue(self.db.add_role_mapping_entry(kind, 16, 4, 160003))
        self.assertTrue(self.db.add_role_mapping_entry(kind, 16, 4, 160004))
        self.assertEqual(self.db.get_role_id_for_channel_division(kind=kind, channel_id=16, division=3), 160003)
        self.assertEqual(self.db.get_role_id_for_channel_division(kind=kind, channel_id=16, division=4), 160004)
        self.assertTrue(self.db.remove_role_mapping(kind, 16, 3))
        self.assertTrue(self.db.remove_kind_notification_channel(kind, 16))
        self.assertFalse(self.db.remove_kind_notification_channel(kind, 16))
        self.assertFalse(self.db.get_role_id_for_channel_division(kind=kind, channel_id=16, division=4))
        self.assertFalse(self.db.get_role_id_for_channel_division(kind=kind, channel_id=16, division=5))
        self.assertRaises(RuntimeError, self.db.get_notification_channel_id, "non-existant")


class TestRegexes(unittest.TestCase):
    def test_events(self):
        for event in constants.events:
            self.assertTrue(isinstance(event, constants.EventKind))
            self.assertTrue(event.slug)
            self.assertTrue(event.name)
            self.assertTrue(isinstance(event.regex, re.Pattern))
            self.assertTrue(event.format)


if __name__ == "__main__":
    unittest.main()

__author__ = 'jslvtr'

import unittest
from src.db.models import User, Group, Invite
from src.app.app import app
from flask import g
from src.db.database import Database
from werkzeug.security import check_password_hash


class ModelsTest(unittest.TestCase):
    def setUp(self):
        self.app_context = app.app_context()
        with self.app_context:
            g.database = Database('mongodb://admin:admin@ds063879.mongolab.com:63879/heroku_app34205970')

    def tearDown(self):
        with self.app_context:
            g.database = None

    def test_create_user(self):
        user = self._sample_user()

        self.assertEqual(user.email, "test123@gmail.com")
        self.assertTrue(check_password_hash(user.password, "jose"))

    def test_register_user(self):
        with self.app_context:
            user = User.register(email="test123@paco.com",
                                 password="paco")

            user.save()

            user_test = User.get_by_id(user.id)
            self.assertIsNotNone(user_test.access_token)
            self.assertEqual(user.email, "test123@paco.com")
            self.assertTrue(check_password_hash(user.password, "paco"))

            User.remove(user.id)

    def test_save_user(self):
        user = self._sample_user()
        with self.app_context:
            user.save()
            User.remove(user.id)

    def test_update_user_location(self):
        user = self._sample_user()

        with self.app_context:
            user.save()

            User.update_location(user.id, 57.062, 13.673)

            user_test = User.get_by_id(user.id)
            self.assertEqual(user_test.location[0], 57.062)
            self.assertEqual(user_test.location[1], 13.673)
            User.remove(user.id)

    def test_get_groups_of_user(self):
        pass

    def _sample_user(self):
        user = User.create(email="test123@gmail.com",
                           password="jose")
        return user

    def _sample_group(self, creator):
        group = Group.create(group_id="1234",
                             creator=creator.id,
                             name="Test group")
        return group

    def test_create_group(self):
        group_dict = self._sample_group(self._sample_user()).to_dict()

        self.assertEqual(group_dict['id'], "1234")
        self.assertEqual(group_dict['name'], "Test group")

    def test_add_member_to_group(self):
        user = self._sample_user()
        group = self._sample_group(user)

        with self.app_context:
            Group.remove(group.id)
            User.remove(user.id)

            user.save()
            group.save()

            Group.add_member(group.id, "1234")

            group_test = Group.get_by_id(group.id)

            Group.remove(group.id)
            User.remove(user.id)

            self.assertTrue("1234" in group_test.users)

    def test_get_group_members(self):
        user = self._sample_user()
        group = self._sample_group(user)

        with self.app_context:
            Group.remove(group.id)
            User.remove(user.id)

            user.save()
            group.save()

            ret = []

            for friend_id in group.users:
                friend = User.get_by_id(friend_id)
                ret.extend([{'friend_id': friend_id,
                             'name': friend.email,
                             'location': friend.location}])

            self.assertGreater(len(ret), 0)

            Group.remove(group.id)
            User.remove(user.id)

    def test_create_email_invite(self):
        inviter = self._sample_user()
        invite = Invite.create("test123@gmail.com", inviter.id)

        self.assertEqual(invite.email, "test123@gmail.com")
        self.assertEqual(invite.inviter_id, inviter.id)
        self.assertIsNotNone(invite.token)
        self.assertIsNotNone(invite.created_date)
        self.assertTrue(invite.pending)

    def test_activate_email_invite(self):
        inviter = self._sample_user()
        invite = Invite.create("test123@gmail.com", inviter.id)

        with self.app_context:
            invite.save()
            Invite.activate(invite.token, "pass")
            user = User.get_by_email(invite.email)
            self.assertIsNotNone(user)
            self.assertEqual(user.email, invite.email)
            User.remove(user.id)
            Group.remove_member(invite.inviter_id, user.id)


if __name__ == '__main__':
    unittest.main()

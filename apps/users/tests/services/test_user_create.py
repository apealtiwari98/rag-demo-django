from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.users.models import BaseUser
from apps.users.services import user_create


class UserCreateTests(TestCase):
    def test_user_create_lowercases_email_and_hashes_password(self):
        user = user_create(email="Ada@Example.com", password="password123")

        self.assertEqual(user.email, "ada@example.com")
        self.assertTrue(user.check_password("password123"))
        self.assertFalse(user.is_admin)

    def test_user_create_without_password_sets_unusable_password(self):
        user = user_create(email="ada@example.com")

        self.assertFalse(user.has_usable_password())

    def test_user_create_rejects_duplicate_email(self):
        user_create(email="ada@example.com")

        with self.assertRaises(ValidationError):
            user_create(email="ADA@example.com")

        self.assertEqual(BaseUser.objects.count(), 1)

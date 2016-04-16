from unittest.case import TestCase


class AuthenticationTests(TestCase):
    def test_sign_in(self):
        """
        Tries to sign in to an existing account.
        """
        pass

    def test_sign_in_wrong_username(self):
        """
        Tries to sign in to a not existing account.
        """
        pass

    def test_sign_in_wrong_password(self):
        """
        Tries to sign in with correct username and wrong password.
        """
        pass

    def test_sign_up(self):
        """
        Tries to sign up with correct username.
        """
        pass

    def test_sign_up_used_username(self):
        """
        Tries to sign up with used username.
        """
        pass

    def test_sign_up_empty_password(self):
        """
        Tries to sign up with empty password (should pass)
        """
        pass

    def test_sign_up_empty_username(self):
        """
        Tries to sign up with empty username (should not pass)
        """
        pass

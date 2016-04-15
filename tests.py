import unittest


def load_tests():
    suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
    return suite

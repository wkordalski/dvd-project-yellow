import unittest


def load_tests(loader=None, tests=None, pattern=None):
    suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
    return suite

if __name__ == '__main__':
    unittest.main()

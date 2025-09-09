import unittest


def main():
    loader = unittest.TestLoader()
    suite = loader.discover('tests')

    runner = unittest.TextTestRunner()
    runner.run(suite)


if __name__ == '__main__':
    main()

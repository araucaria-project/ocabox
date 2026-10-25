import unittest
from importlib.metadata import PackageNotFoundError

from ocaboxapi.dependency_guard import check_dependency_versions


class ImportGuardTest(unittest.TestCase):

    def test_rejects_old_obcom(self):
        with self.assertRaises(ImportError) as ctx:
            check_dependency_versions(installed=lambda dist: '1.4.0')
        self.assertIn('1.13.0', str(ctx.exception))

    def test_accepts_required_and_newer(self):
        check_dependency_versions(installed=lambda dist: '1.13.0')
        check_dependency_versions(installed=lambda dist: '1.14.0')

    def test_missing_distribution_is_import_error(self):
        def _missing(_dist):
            raise PackageNotFoundError('missing')

        with self.assertRaises(ImportError):
            check_dependency_versions(installed=_missing)

    def test_current_environment_passes(self):
        check_dependency_versions()


if __name__ == '__main__':
    unittest.main()

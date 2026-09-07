"""Refuse to import against an ocabox-common older than the API this package calls."""
from importlib.metadata import PackageNotFoundError, version

from packaging.version import Version

REQUIRED = {'ocabox-common': '1.4.0'}


def check_dependency_versions(installed=version) -> None:
    for dist, minimum in REQUIRED.items():
        try:
            found = installed(dist)
        except PackageNotFoundError as e:
            raise ImportError(f'{dist} is not installed; ocaboxapi requires >= {minimum}') from e
        if Version(found) < Version(minimum):
            raise ImportError(f'ocaboxapi requires {dist} >= {minimum}, found {found}')

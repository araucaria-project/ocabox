from setuptools import setup
import ocabox_bases as base

setup(
    name='ocabox',
    version=base.__version__,
    packages=[''],
    url='',
    license=base.__license__,
    author=base.__author__,
    author_email=base.__email__,
    description='',
    include_package_data=True,
    python_requires='>=3.8',
    install_requires=[
        'setuptools~=62.1.0',
        'pyzmq~=22.3.0',
        'msgpack~=1.0.3',
    ],
    dependency_links=[

    ],
)

from importlib.metadata import PackageNotFoundError, version

__author__ = " Ernest Lasek (elasek@akond.com), Mikołaj Kałuszyński (mkalusz@camk.edu.pl)"
__copyright__ = ""
__credits__ = ["Ernest Lasek (elasek@akond.com)", "Mikołaj Kałuszyński (mkalusz@camk.edu.pl)"]
__license__ = "MIT"
try:
    __version__ = version("ocabox")
except PackageNotFoundError:
    __version__ = "0.0.0+uninstalled"
__maintainer__ = "Mikołaj Kałuszyński (mkalusz@camk.edu.pl)"
__email__ = "mkalusz@camk.edu.pl"
__status__ = "Development"

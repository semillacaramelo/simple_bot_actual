# Package initialization
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("deriv-backtesting")
except PackageNotFoundError:
    __version__ = "0.1.0.dev"

# Make key modules available at package level
from src.api import deriv_connector, data_fetcher
from src.execution import order_executor
from src.strategy import strategy_executor, moving_average
from backtesting import engine, simulator
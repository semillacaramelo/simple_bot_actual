import logging
import colorama
from colorama import Fore, Back, Style

# Initialize colorama
colorama.init(autoreset=True)

# --- Colors ---
COLOR_RESET = Style.RESET_ALL
COLOR_CYAN = Fore.CYAN
COLOR_BLUE = Fore.BLUE
COLOR_YELLOW = Fore.YELLOW
COLOR_MAGENTA = Fore.MAGENTA
COLOR_GREEN = Fore.GREEN
COLOR_RED = Fore.RED
COLOR_WHITE = Fore.WHITE

# --- Icons ---
ICON_ROCKET = "🚀"  # Initialization
ICON_CHART = "📊"   # Data Processing
ICON_LIGHT_BULB = "💡" # Signals
ICON_WARNING = "⚠️"  # Warnings
ICON_CHECK_MARK = "✅" # Success
ICON_ERROR = "❌"   # Error
ICON_WAIT = "⏳"    # Waiting

def colored_print(color, icon, message):
    """Prints message to console with color and icon."""
    print(f"{color}{icon} {message}{COLOR_RESET}")

def cyan_status(message):
    colored_print(COLOR_CYAN, ICON_ROCKET, message)

def blue_status(message):
    colored_print(COLOR_BLUE, ICON_CHART, message)

def yellow_signal(message):
    colored_print(COLOR_YELLOW, ICON_LIGHT_BULB, message)

def magenta_warning(message):
    colored_print(COLOR_MAGENTA, ICON_WARNING, message)

def green_success(message):
    colored_print(COLOR_GREEN, ICON_CHECK_MARK, message)

def red_error(message):
    colored_print(COLOR_RED, ICON_ERROR, message)

def white_wait(message):
    colored_print(COLOR_WHITE, ICON_WAIT, message)

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add color and icons to log messages."""

    FORMATS = {
        logging.DEBUG:    COLOR_BLUE + ICON_CHART + " DEBUG: %(message)s" + COLOR_RESET,
        logging.INFO:     COLOR_GREEN + ICON_CHECK_MARK + " INFO: %(message)s" + COLOR_RESET,
        logging.WARNING:  COLOR_YELLOW + ICON_WARNING + " WARNING: %(message)s" + COLOR_RESET,
        logging.ERROR:    COLOR_RED + ICON_ERROR + " ERROR: %(message)s" + COLOR_RESET,
        logging.CRITICAL: COLOR_RED + ICON_ERROR + " CRITICAL: %(message)s" + COLOR_RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, COLOR_WHITE + ICON_WAIT + " %(levelname)s: %(message)s" + COLOR_RESET)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Example usage (for testing)
if __name__ == '__main__':
    cyan_status("Initializing bot...")
    blue_status("Fetching market data...")
    yellow_signal("Potential BUY signal detected!")
    magenta_warning("API connection unstable.")
    green_success("Trade executed successfully.")
    red_error("Order placement failed.")
    white_wait("Waiting for market open...")

    logger = logging.getLogger('colored_logger')
    logger.setLevel(logging.DEBUG)

    # Create console handler and set formatter
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Test logger
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
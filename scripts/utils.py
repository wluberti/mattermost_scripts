import logging
import sys

def setup_logging(debug: bool = False):
    """Configures logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def get_logger(name: str):
    """Returns a logger instance with the given name."""
    return logging.getLogger(name)

def confirm_action(message: str) -> bool:
    """Asks the user for confirmation (Y/n)."""
    response = input(f"{message} (y/N): ").strip().lower()
    return response == 'y'

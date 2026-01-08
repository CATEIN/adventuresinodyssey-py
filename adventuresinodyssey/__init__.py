"""
Adventures in Odyssey API Package
"""
from .clubclient import ClubClient
from .aioclient import AIOClient

__version__ = "0.1.7"
__all__ = ["ClubClient", "AIOClient"]

import logging

def set_logging_level(level: str = 'INFO'):
    """
    Sets the logging level for the 'adventuresinodyssey' package and its modules.
    
    Args:
        level: The desired logging level (e.g., 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
    """
    # 1. Map string level to logging constants
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid logging level: {level}. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL.")
        
    # 2. Get the root logger for the entire package ('adventuresinodyssey')
    package_logger = logging.getLogger('adventuresinodyssey')
    package_logger.setLevel(numeric_level)
    
    # 3. If a handler hasn't been configured (i.e., the user hasn't called basicConfig), 
    # ensure logging output goes somewhere by attaching a basic handler.
    if not logging.root.handlers:
        logging.basicConfig(level=numeric_level)
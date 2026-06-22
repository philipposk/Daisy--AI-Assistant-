"""
Logging utilities
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(name: str = "daisy", log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    """Setup and return a logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file = Path(log_file).expanduser()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "daisy") -> logging.Logger:
    """Get an existing logger or create a new one"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


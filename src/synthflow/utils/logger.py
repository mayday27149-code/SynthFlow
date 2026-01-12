import logging
import sys
from typing import Optional

def setup_logger(name: str = "synthflow", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(level)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    logger_name = "synthflow"
    if name:
        logger_name = f"synthflow.{name}"
    return logging.getLogger(logger_name)

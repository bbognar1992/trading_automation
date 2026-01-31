"""
Configuration file for the TradingView-IBKR middleman application.
"""

import os
from typing import Optional


class Config:
    """Application configuration."""
    
    # FastAPI settings
    FLASK_HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')  # Kept for backward compatibility
    FLASK_PORT: int = int(os.getenv('FLASK_PORT', 8000))  # Changed default to 8000 (FastAPI convention)
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'  # Enables auto-reload
    
    # IB Gateway/TWS settings
    IB_HOST: str = os.getenv('IB_HOST', '127.0.0.1')
    IB_PORT: int = int(os.getenv('IB_PORT', 7497))  # 7497 for TWS paper, 4001 for Gateway paper
    IB_CLIENT_ID: int = int(os.getenv('IB_CLIENT_ID', 1))
    
    # Security (optional webhook secret for validation)
    WEBHOOK_SECRET: Optional[str] = os.getenv('WEBHOOK_SECRET', None)
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')


# Common IB Gateway ports:
# - 7497: TWS Paper Trading
# - 7496: TWS Live Trading
# - 4001: IB Gateway Paper Trading
# - 4002: IB Gateway Live Trading


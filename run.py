"""
Run script for the IoT Sensor Monitoring System
"""

import os
import sys
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.main import app
import uvicorn

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting IoT Sensor Monitoring System...")
    logger.info("Dashboard will be available at: http://localhost:8000/docs")
    logger.info("WebSocket endpoint: ws://localhost:8000/ws")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

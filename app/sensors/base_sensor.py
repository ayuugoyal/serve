import time
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseSensor(ABC):
    def __init__(self, sensor_id: str, asset_id: str, zone_id: str = "Zone-1"):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.zone_id = zone_id
        self.last_reading_time = None
        self.lock = Lock()
        self.current_reading = {}
        self.is_active = False
        
    @abstractmethod
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        """Read data from the physical sensor"""
        pass
    
    @abstractmethod
    def get_sensor_type(self) -> str:
        """Return the sensor type identifier"""
        pass
    
    def update_reading(self):
        """Update the sensor reading"""
        try:
            data = self.read_sensor_data()
            if data is not None:
                with self.lock:
                    self.current_reading = data
                    self.last_reading_time = datetime.now(timezone.utc)
                    self.is_active = True
            else:
                self.is_active = False
        except Exception as e:
            logger.error(f"Error updating {self.sensor_id}: {e}")
            self.is_active = False
    
    def get_reading(self) -> Dict[str, Any]:
        """Get the current sensor reading"""
        with self.lock:
            status = 'active' if self.is_active else 'inactive'
            
            return {
                'sensor_type': self.get_sensor_type(),
                'sensor_id': self.sensor_id,
                'assetId': self.asset_id,
                'zone_id': self.zone_id,
                'timestamp': self.last_reading_time.isoformat() if self.last_reading_time else None,
                'status': status,
                **self.current_reading
            }
    
    def is_healthy(self) -> bool:
        """Check if sensor is healthy"""
        if not self.last_reading_time:
            return False
        
        time_since_reading = (datetime.now(timezone.utc) - self.last_reading_time).total_seconds()
        return time_since_reading < 30  # Healthy if reading within last 30 seconds

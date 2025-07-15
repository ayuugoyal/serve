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
        self.connection_failures = 0
        self.max_connection_failures = 3  # Allow 3 consecutive failures before marking inactive
        
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
                    self.connection_failures = 0  # Reset failure count on successful read
                    if not self.is_active:
                        self.is_active = True
                        logger.info(f"Sensor {self.sensor_id} reconnected")
            else:
                # Increment failure count
                self.connection_failures += 1
                if self.connection_failures >= self.max_connection_failures:
                    if self.is_active:
                        logger.warning(f"Sensor {self.sensor_id} marked as inactive after {self.connection_failures} failures")
                    self.is_active = False
                    with self.lock:
                        self.current_reading = {}  # Clear readings for inactive sensor
                        
        except Exception as e:
            logger.error(f"Error updating {self.sensor_id}: {e}")
            self.connection_failures += 1
            if self.connection_failures >= self.max_connection_failures:
                self.is_active = False
                with self.lock:
                    self.current_reading = {}
    
    def get_reading(self) -> Dict[str, Any]:
        """Get the current sensor reading"""
        with self.lock:
            base_info = {
                'sensor_type': self.get_sensor_type(),
                'sensor_id': self.sensor_id,
                'assetId': self.asset_id,
                'zone_id': self.zone_id,
                'timestamp': self.last_reading_time.isoformat() if self.last_reading_time else None,
                'status': 'active' if self.is_active else 'inactive'
            }
            
            # Only include sensor data if the sensor is active
            if self.is_active and self.current_reading:
                base_info.update(self.current_reading)
            else:
                # For inactive sensors, don't include sensor data
                base_info['message'] = 'Sensor not connected or not responding'
            
            return base_info
    
    def is_healthy(self) -> bool:
        """Check if sensor is healthy"""
        if not self.is_active:
            return False
            
        if not self.last_reading_time:
            return False
        
        time_since_reading = (datetime.now(timezone.utc) - self.last_reading_time).total_seconds()
        return time_since_reading < 30  # Healthy if reading within last 30 seconds
    
    def reset_connection(self):
        """Reset connection failure counter - useful for manual reconnection attempts"""
        self.connection_failures = 0
        logger.info(f"Connection failure counter reset for sensor {self.sensor_id}")
    
    def force_reconnect(self):
        """Force a reconnection attempt by calling setup_pins if available"""
        if hasattr(self, 'setup_pins'):
            logger.info(f"Attempting to reconnect sensor {self.sensor_id}")
            self.reset_connection()
            self.setup_pins()
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
        self.max_connection_failures = 5  # Increased from 3 to 5
        self.consecutive_failed_reads = 0  # Track consecutive failures
        
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
                    self.connection_failures = 0  # Reset failure count
                    self.consecutive_failed_reads = 0  # Reset consecutive failures
                    if not self.is_active:
                        self.is_active = True
                        logger.info(f"Sensor {self.sensor_id} reconnected")
            else:
                # Only increment if sensor was previously active
                if self.is_active:
                    self.consecutive_failed_reads += 1
                    
                    # Only mark as inactive after several consecutive failures
                    if self.consecutive_failed_reads >= self.max_connection_failures:
                        logger.warning(f"Sensor {self.sensor_id} marked as inactive after {self.consecutive_failed_reads} consecutive failed reads")
                        self.is_active = False
                        with self.lock:
                            self.current_reading = {}
                        self.connection_failures += 1
                else:
                    # If sensor is already inactive, just log occasionally
                    if self.consecutive_failed_reads % 60 == 0:  # Log every 60 attempts
                        logger.debug(f"Sensor {self.sensor_id} still inactive")
                        
        except Exception as e:
            logger.error(f"Error updating {self.sensor_id}: {e}")
            if self.is_active:
                self.consecutive_failed_reads += 1
                if self.consecutive_failed_reads >= self.max_connection_failures:
                    self.is_active = False
                    self.connection_failures += 1
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
                'status': 'active' if self.is_active else 'inactive',
                'consecutive_failures': self.consecutive_failed_reads
            }
            
            # Always include current reading data, even if sensor is inactive
            if self.current_reading:
                base_info.update(self.current_reading)
            else:
                base_info['message'] = f'No data - {self.consecutive_failed_reads} consecutive failures'
            
            return base_info
    
    def is_healthy(self) -> bool:
        """Check if sensor is healthy"""
        if not self.is_active:
            return False
            
        if not self.last_reading_time:
            return False
        
        time_since_reading = (datetime.now(timezone.utc) - self.last_reading_time).total_seconds()
        return time_since_reading < 60  # Healthy if reading within last 60 seconds (increased from 30)
    
    def reset_connection(self):
        """Reset connection failure counter"""
        self.connection_failures = 0
        self.consecutive_failed_reads = 0
        logger.info(f"Connection failure counter reset for sensor {self.sensor_id}")
    
    def force_reconnect(self):
        """Force a reconnection attempt"""
        logger.info(f"Attempting to reconnect sensor {self.sensor_id}")
        self.reset_connection()
        if hasattr(self, 'setup_pins'):
            self.setup_pins()
        # Try a test reading
        self.update_reading()
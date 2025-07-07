import logging
from typing import Dict, List, Any
from .sensor_implementations import *

logger = logging.getLogger(__name__)

class SensorManager:
    def __init__(self):
        self.sensors = {
            'ultrasonic': UltrasonicSensor(),
            'air_quality': MQ135Sensor(),
            'temperature_humidity': DHT11Sensor(),
            'light_sensor': LDRSensor(),
            'motion_sensor': PIRSensor()
        }
        logger.info(f"Initialized {len(self.sensors)} sensors")
    
    def update_all_sensors(self):
        """Update all sensor readings"""
        for sensor_type, sensor in self.sensors.items():
            try:
                sensor.update_reading()
            except Exception as e:
                logger.error(f"Error updating {sensor_type}: {e}")
    
    def get_all_readings(self) -> List[Dict[str, Any]]:
        """Get readings from all sensors"""
        readings = []
        for sensor_type, sensor in self.sensors.items():
            try:
                reading = sensor.get_reading()
                readings.append(reading)
            except Exception as e:
                logger.error(f"Error getting reading from {sensor_type}: {e}")
                readings.append({
                    'sensor_type': sensor_type,
                    'status': 'error',
                    'error': str(e)
                })
        return readings
    
    def get_sensor_reading(self, sensor_type: str) -> Dict[str, Any]:
        """Get reading from specific sensor"""
        if sensor_type not in self.sensors:
            return None
        
        try:
            return self.sensors[sensor_type].get_reading()
        except Exception as e:
            logger.error(f"Error getting {sensor_type} reading: {e}")
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all sensors"""
        health_status = {}
        for sensor_type, sensor in self.sensors.items():
            health_status[sensor_type] = {
                'healthy': sensor.is_healthy(),
                'active': sensor.is_active,
                'last_reading': sensor.last_reading_time.isoformat() if sensor.last_reading_time else None
            }
        return health_status
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        total_sensors = len(self.sensors)
        active_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_active)
        healthy_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_healthy())
        
        return {
            'total_sensors': total_sensors,
            'active_sensors': active_sensors,
            'healthy_sensors': healthy_sensors,
            'system_health': 'healthy' if healthy_sensors == total_sensors else 'degraded'
        }
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if not SIMULATION_MODE:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                logger.info("GPIO cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

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
        active_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_active)
        total_sensors = len(self.sensors)
        logger.info(f"Initialized {total_sensors} sensors. Active: {active_sensors}")
    
    def update_all_sensors(self):
        """Update all sensor readings"""
        for sensor_type, sensor in self.sensors.items():
            if sensor.is_active:
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
                if not sensor.is_active:
                    reading['status'] = 'not active'
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
        
        sensor = self.sensors[sensor_type]
        try:
            reading = sensor.get_reading()
            if not sensor.is_active:
                reading['status'] = 'not active'
            return reading
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
            'system_health': 'healthy' if healthy_sensors == active_sensors else 'degraded'
        }
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
            logger.info("GPIO cleaned up")
        except (ImportError, RuntimeError):
            pass  # GPIO module not available or already cleaned up
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

import logging
import time
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
        self.diagnostics = {
            'startup_time': time.time(),
            'total_updates': 0,
            'sensor_stats': {}
        }
        
        # Initialize sensor stats
        for sensor_type, sensor in self.sensors.items():
            self.diagnostics['sensor_stats'][sensor_type] = {
                'successful_reads': 0,
                'failed_reads': 0,
                'last_success': None,
                'last_failure': None,
                'total_activations': 1 if sensor.is_active else 0,
                'total_deactivations': 0
            }
        
        active_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_active)
        total_sensors = len(self.sensors)
        logger.info(f"Initialized {total_sensors} sensors. Active: {active_sensors}")
        
        # Log individual sensor status
        for sensor_type, sensor in self.sensors.items():
            status = "ACTIVE" if sensor.is_active else "INACTIVE"
            logger.info(f"  {sensor_type}: {status}")
    
    def update_all_sensors(self):
        """Update all sensor readings with enhanced diagnostics"""
        self.diagnostics['total_updates'] += 1
        
        for sensor_type, sensor in self.sensors.items():
            was_active = sensor.is_active
            
            try:
                sensor.update_reading()
                
                # Track state changes
                if was_active != sensor.is_active:
                    if sensor.is_active:
                        self.diagnostics['sensor_stats'][sensor_type]['total_activations'] += 1
                        logger.info(f"Sensor {sensor_type} REACTIVATED")
                    else:
                        self.diagnostics['sensor_stats'][sensor_type]['total_deactivations'] += 1
                        logger.warning(f"Sensor {sensor_type} DEACTIVATED after {sensor.consecutive_failed_reads} failures")
                
                # Track success/failure stats
                if sensor.current_reading:
                    self.diagnostics['sensor_stats'][sensor_type]['successful_reads'] += 1
                    self.diagnostics['sensor_stats'][sensor_type]['last_success'] = time.time()
                else:
                    self.diagnostics['sensor_stats'][sensor_type]['failed_reads'] += 1
                    self.diagnostics['sensor_stats'][sensor_type]['last_failure'] = time.time()
                    
            except Exception as e:
                logger.error(f"Error updating {sensor_type}: {e}")
                self.diagnostics['sensor_stats'][sensor_type]['failed_reads'] += 1
                self.diagnostics['sensor_stats'][sensor_type]['last_failure'] = time.time()
    
    def get_all_readings(self) -> List[Dict[str, Any]]:
        """Get readings from all sensors"""
        readings = []
        for sensor_type, sensor in self.sensors.items():
            try:
                reading = sensor.get_reading()
                # Add diagnostic info
                reading['diagnostic_info'] = {
                    'consecutive_failures': sensor.consecutive_failed_reads,
                    'connection_failures': sensor.connection_failures,
                    'uptime_minutes': (time.time() - self.diagnostics['startup_time']) / 60
                }
                readings.append(reading)
            except Exception as e:
                logger.error(f"Error getting reading from {sensor_type}: {e}")
                readings.append({
                    'sensor_type': sensor_type,
                    'status': 'error',
                    'error': str(e),
                    'consecutive_failures': getattr(sensor, 'consecutive_failed_reads', 0)
                })
        return readings
    
    def get_sensor_reading(self, sensor_type: str) -> Dict[str, Any]:
        """Get reading from specific sensor"""
        if sensor_type not in self.sensors:
            return None
        
        sensor = self.sensors[sensor_type]
        try:
            reading = sensor.get_reading()
            # Add diagnostic info
            reading['diagnostic_info'] = {
                'consecutive_failures': sensor.consecutive_failed_reads,
                'connection_failures': sensor.connection_failures,
                'max_failures_threshold': sensor.max_connection_failures
            }
            return reading
        except Exception as e:
            logger.error(f"Error getting {sensor_type} reading: {e}")
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all sensors"""
        health_status = {}
        for sensor_type, sensor in self.sensors.items():
            stats = self.diagnostics['sensor_stats'][sensor_type]
            health_status[sensor_type] = {
                'healthy': sensor.is_healthy(),
                'active': sensor.is_active,
                'last_reading': sensor.last_reading_time.isoformat() if sensor.last_reading_time else None,
                'consecutive_failures': sensor.consecutive_failed_reads,
                'total_successful_reads': stats['successful_reads'],
                'total_failed_reads': stats['failed_reads'],
                'success_rate': stats['successful_reads'] / max(1, stats['successful_reads'] + stats['failed_reads']) * 100,
                'activations': stats['total_activations'],
                'deactivations': stats['total_deactivations']
            }
        return health_status
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        total_sensors = len(self.sensors)
        active_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_active)
        healthy_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_healthy())
        
        # Calculate overall stats
        total_successful = sum(stats['successful_reads'] for stats in self.diagnostics['sensor_stats'].values())
        total_failed = sum(stats['failed_reads'] for stats in self.diagnostics['sensor_stats'].values())
        overall_success_rate = total_successful / max(1, total_successful + total_failed) * 100
        
        return {
            'total_sensors': total_sensors,
            'active_sensors': active_sensors,
            'healthy_sensors': healthy_sensors,
            'system_health': 'healthy' if healthy_sensors == active_sensors else 'degraded',
            'uptime_minutes': (time.time() - self.diagnostics['startup_time']) / 60,
            'total_updates': self.diagnostics['total_updates'],
            'overall_success_rate': round(overall_success_rate, 2),
            'gpio_available': GPIO_AVAILABLE
        }
    
    def force_sensor_reconnect(self, sensor_type: str = None) -> Dict[str, Any]:
        """Force reconnection of specific sensor or all sensors"""
        results = {}
        
        if sensor_type:
            if sensor_type in self.sensors:
                sensor = self.sensors[sensor_type]
                logger.info(f"Forcing reconnection of {sensor_type}")
                sensor.force_reconnect()
                results[sensor_type] = {
                    'reconnected': True,
                    'active': sensor.is_active,
                    'consecutive_failures_reset': sensor.consecutive_failed_reads
                }
            else:
                results[sensor_type] = {'error': 'Sensor not found'}
        else:
            # Reconnect all sensors
            for sensor_type, sensor in self.sensors.items():
                logger.info(f"Forcing reconnection of {sensor_type}")
                sensor.force_reconnect()
                results[sensor_type] = {
                    'reconnected': True,
                    'active': sensor.is_active,
                    'consecutive_failures_reset': sensor.consecutive_failed_reads
                }
        
        return results
    
    def get_troubleshooting_info(self) -> Dict[str, Any]:
        """Get detailed troubleshooting information"""
        troubleshooting = {
            'system_info': {
                'gpio_available': GPIO_AVAILABLE,
                'uptime_minutes': (time.time() - self.diagnostics['startup_time']) / 60,
                'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}"
            },
            'sensor_details': {},
            'common_issues': []
        }
        
        for sensor_type, sensor in self.sensors.items():
            stats = self.diagnostics['sensor_stats'][sensor_type]
            troubleshooting['sensor_details'][sensor_type] = {
                'current_status': 'active' if sensor.is_active else 'inactive',
                'consecutive_failures': sensor.consecutive_failed_reads,
                'max_failure_threshold': sensor.max_connection_failures,
                'total_activations': stats['total_activations'],
                'total_deactivations': stats['total_deactivations'],
                'success_rate': stats['successful_reads'] / max(1, stats['successful_reads'] + stats['failed_reads']) * 100,
                'last_reading_time': sensor.last_reading_time.isoformat() if sensor.last_reading_time else None,
                'pins': getattr(sensor, 'data_pin', None) or {
                    'trigger': getattr(sensor, 'trigger_pin', None),
                    'echo': getattr(sensor, 'echo_pin', None)
                }
            }
            
            # Identify potential issues
            if not sensor.is_active:
                if stats['total_activations'] == 0:
                    troubleshooting['common_issues'].append(f"{sensor_type}: Never activated - check wiring")
                elif stats['total_deactivations'] > 0:
                    troubleshooting['common_issues'].append(f"{sensor_type}: Became inactive - possible loose connection")
            
            if sensor.consecutive_failed_reads > sensor.max_connection_failures // 2:
                troubleshooting['common_issues'].append(f"{sensor_type}: High failure rate - check power/connections")
        
        return troubleshooting
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if GPIO_AVAILABLE:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                logger.info("GPIO cleaned up")
        except (ImportError, RuntimeError):
            pass  # GPIO module not available or already cleaned up
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
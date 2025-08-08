import logging
import time
from typing import Dict, List, Any
from .sensor_implementations import *

logger = logging.getLogger(__name__)

class SensorManager:
    def __init__(self):
        """Initialize all real hardware sensors - NO SIMULATION"""
        self.sensors = {
            # Temperature and Humidity
            'temperature_humidity': DHT22Sensor(
                sensor_id="DHT22-01", 
                asset_id="TEMP-HUM-01", 
                data_pin=22
            ),
            
            # Air Quality
            'air_quality': MQ135Sensor(
                sensor_id="MQ135-01", 
                asset_id="AIR-QUALITY-01",
                digital_pin=25, 
                spi_channel=0, 
                adc_channel=0
            ),
            
            # Light Sensor
            'light_sensor': BH1750Sensor(
                sensor_id="BH1750-01", 
                asset_id="LIGHT-SENSOR-01",
                i2c_address=0x23
            ),
            
            # Dust/Particle Sensor
            'dust_sensor': GP2Y1010AU0FSensor(
                sensor_id="GP2Y1010-01", 
                asset_id="DUST-SENSOR-01",
                led_pin=7, 
                adc_channel=1, 
                spi_channel=0
            ),
            
            # Vibration Sensor
            'vibration_sensor': PiezoVibrationSensor(
                sensor_id="PIEZO-01", 
                asset_id="VIBRATION-SENSOR-01",
                analog_pin=2, 
                threshold=100
            ),
            
            # Motion Radar Sensor
            'motion_radar': HLK_LD2420Sensor(
                sensor_id="LD2420-01", 
                asset_id="MOTION-RADAR-01",
                uart_port="/dev/ttyUSB0", 
                baud_rate=256000
            ),
            
            # Ultrasonic Distance Sensor
            'ultrasonic': UltrasonicSensor(
                sensor_id="HCSR04-01", 
                asset_id="ULTRASONIC-01",
                trigger_pin=18, 
                echo_pin=24
            )
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
        logger.info(f"Initialized {total_sensors} REAL HARDWARE sensors. Active: {active_sensors}")
        
        # Log individual sensor status with hardware details
        for sensor_type, sensor in self.sensors.items():
            status = "ACTIVE" if sensor.is_active else "INACTIVE"
            model = getattr(sensor, 'sensor_model', sensor_type.upper())
            pins_info = ""
            
            # Add pin/connection info for troubleshooting
            if hasattr(sensor, 'data_pin'):
                pins_info = f"(Pin: {sensor.data_pin})"
            elif hasattr(sensor, 'trigger_pin') and hasattr(sensor, 'echo_pin'):
                pins_info = f"(Trigger: {sensor.trigger_pin}, Echo: {sensor.echo_pin})"
            elif hasattr(sensor, 'digital_pin'):
                pins_info = f"(Digital: {sensor.digital_pin})"
            elif hasattr(sensor, 'i2c_address'):
                pins_info = f"(I2C: {hex(sensor.i2c_address)})"
            elif hasattr(sensor, 'uart_port'):
                pins_info = f"(UART: {sensor.uart_port})"
            
            logger.info(f"  {sensor_type}: {status} {pins_info}")
            
            if not sensor.is_active:
                logger.warning(f"    {sensor_type} not active - check wiring/connections")
    
    def update_all_sensors(self):
        """Update all sensor readings - NO SIMULATION, real hardware only"""
        self.diagnostics['total_updates'] += 1
        
        for sensor_type, sensor in self.sensors.items():
            was_active = sensor.is_active
            
            try:
                sensor.update_reading()
                
                # Track state changes
                if was_active != sensor.is_active:
                    if sensor.is_active:
                        self.diagnostics['sensor_stats'][sensor_type]['total_activations'] += 1
                        logger.info(f"✅ {sensor_type} RECONNECTED")
                    else:
                        self.diagnostics['sensor_stats'][sensor_type]['total_deactivations'] += 1
                        logger.warning(f"❌ {sensor_type} DISCONNECTED after {sensor.consecutive_failed_reads} failures")
                
                # Track success/failure stats
                if sensor.current_reading:
                    self.diagnostics['sensor_stats'][sensor_type]['successful_reads'] += 1
                    self.diagnostics['sensor_stats'][sensor_type]['last_success'] = time.time()
                    
                    # Log successful readings periodically (every 100 reads)
                    if self.diagnostics['sensor_stats'][sensor_type]['successful_reads'] % 100 == 0:
                        logger.debug(f"{sensor_type}: {self.diagnostics['sensor_stats'][sensor_type]['successful_reads']} successful reads")
                else:
                    self.diagnostics['sensor_stats'][sensor_type]['failed_reads'] += 1
                    self.diagnostics['sensor_stats'][sensor_type]['last_failure'] = time.time()
                    
                    # Log failures more frequently for troubleshooting
                    if sensor.consecutive_failed_reads > 0 and sensor.consecutive_failed_reads % 10 == 0:
                        logger.debug(f"{sensor_type}: {sensor.consecutive_failed_reads} consecutive failures")
                    
            except Exception as e:
                logger.error(f"Error updating {sensor_type}: {e}")
                self.diagnostics['sensor_stats'][sensor_type]['failed_reads'] += 1
                self.diagnostics['sensor_stats'][sensor_type]['last_failure'] = time.time()
    
    def get_all_readings(self) -> List[Dict[str, Any]]:
        """Get readings from all sensors - real data only"""
        readings = []
        for sensor_type, sensor in self.sensors.items():
            try:
                reading = sensor.get_reading()
                
                # Add diagnostic info
                reading['diagnostic_info'] = {
                    'consecutive_failures': sensor.consecutive_failed_reads,
                    'connection_failures': sensor.connection_failures,
                    'uptime_minutes': (time.time() - self.diagnostics['startup_time']) / 60,
                    'hardware_type': 'REAL_SENSOR',  # Clearly mark as real hardware
                    'simulation': False  # Explicitly state no simulation
                }
                
                # Add hardware-specific info
                if hasattr(sensor, 'warmup_time') and hasattr(sensor, 'start_time'):
                    reading['diagnostic_info']['warmup_status'] = sensor.is_warmed_up()
                
                readings.append(reading)
                
            except Exception as e:
                logger.error(f"Error getting reading from {sensor_type}: {e}")
                readings.append({
                    'sensor_type': sensor_type,
                    'status': 'error',
                    'error': str(e),
                    'consecutive_failures': getattr(sensor, 'consecutive_failed_reads', 0),
                    'hardware_type': 'REAL_SENSOR',
                    'simulation': False
                })
        return readings
    
    def get_sensor_reading(self, sensor_type: str) -> Dict[str, Any]:
        """Get reading from specific sensor - real data only"""
        if sensor_type not in self.sensors:
            return {
                'sensor_type': sensor_type,
                'status': 'not_found',
                'error': f'Sensor {sensor_type} not found',
                'hardware_type': 'REAL_SENSOR',
                'simulation': False
            }
        
        sensor = self.sensors[sensor_type]
        try:
            reading = sensor.get_reading()
            
            # Add diagnostic info
            reading['diagnostic_info'] = {
                'consecutive_failures': sensor.consecutive_failed_reads,
                'connection_failures': sensor.connection_failures,
                'max_failures_threshold': sensor.max_connection_failures,
                'hardware_type': 'REAL_SENSOR',
                'simulation': False
            }
            
            return reading
            
        except Exception as e:
            logger.error(f"Error getting {sensor_type} reading: {e}")
            return {
                'sensor_type': sensor_type,
                'status': 'error',
                'error': str(e),
                'hardware_type': 'REAL_SENSOR',
                'simulation': False
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all sensors"""
        health_status = {}
        for sensor_type, sensor in self.sensors.items():
            stats = self.diagnostics['sensor_stats'][sensor_type]
            
            # Calculate success rate
            total_attempts = stats['successful_reads'] + stats['failed_reads']
            success_rate = (stats['successful_reads'] / max(1, total_attempts)) * 100
            
            health_status[sensor_type] = {
                'healthy': sensor.is_healthy(),
                'active': sensor.is_active,
                'last_reading': sensor.last_reading_time.isoformat() if sensor.last_reading_time else None,
                'consecutive_failures': sensor.consecutive_failed_reads,
                'total_successful_reads': stats['successful_reads'],
                'total_failed_reads': stats['failed_reads'],
                'success_rate': round(success_rate, 2),
                'activations': stats['total_activations'],
                'deactivations': stats['total_deactivations'],
                'hardware_type': 'REAL_SENSOR',
                'simulation': False
            }
            
            # Add sensor-specific info
            if hasattr(sensor, 'warmup_time'):
                health_status[sensor_type]['warmup_required'] = sensor.warmup_time
                health_status[sensor_type]['warmed_up'] = sensor.is_warmed_up()
            
        return health_status
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        total_sensors = len(self.sensors)
        active_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_active)
        healthy_sensors = sum(1 for sensor in self.sensors.values() if sensor.is_healthy())
        
        # Calculate overall stats
        total_successful = sum(stats['successful_reads'] for stats in self.diagnostics['sensor_stats'].values())
        total_failed = sum(stats['failed_reads'] for stats in self.diagnostics['sensor_stats'].values())
        overall_success_rate = (total_successful / max(1, total_successful + total_failed)) * 100
        
        return {
            'total_sensors': total_sensors,
            'active_sensors': active_sensors,
            'healthy_sensors': healthy_sensors,
            'system_health': 'healthy' if healthy_sensors == active_sensors else 'degraded',
            'uptime_minutes': round((time.time() - self.diagnostics['startup_time']) / 60, 2),
            'total_updates': self.diagnostics['total_updates'],
            'overall_success_rate': round(overall_success_rate, 2),
            'gpio_available': GPIO_AVAILABLE,
            'spi_available': SPI_AVAILABLE,
            'hardware_mode': 'REAL_SENSORS_ONLY',
            'simulation': False
        }
    
    def get_hardware_requirements(self) -> Dict[str, Any]:
        """Get hardware requirements and setup instructions"""
        requirements = {
            'python_packages': [
                'RPi.GPIO>=0.7.1',
                'Adafruit-DHT>=1.4.0',
                'spidev>=3.5',
                'smbus2>=0.4.0',
                'pyserial>=3.5'
            ],
            'hardware_connections': {
                'DHT22': {
                    'pins': {'data': 22},
                    'power': '3.3V or 5V',
                    'notes': 'Pull-up resistor (4.7kΩ) may be required'
                },
                'MQ135': {
                    'pins': {'digital': 25, 'analog': 'ADC Channel 0'},
                    'power': '5V',
                    'notes': '3 minute warmup time required, needs ADC for PPM readings'
                },
                'BH1750': {
                    'pins': {'SDA': 'GPIO2', 'SCL': 'GPIO3'},
                    'power': '3.3V',
                    'notes': 'I2C sensor, address 0x23'
                },
                'GP2Y1010AU0F': {
                    'pins': {'LED': 7, 'analog': 'ADC Channel 1'},
                    'power': '5V',
                    'notes': 'Requires ADC for readings, LED control pin needed'
                },
                'Piezo_Vibration': {
                    'pins': {'analog': 'ADC Channel 2'},
                    'power': '3.3V or 5V',
                    'notes': 'Analog sensor, requires ADC'
                },
                'HLK_LD2420': {
                    'pins': {'UART': '/dev/ttyUSB0'},
                    'power': '5V',
                    'notes': 'UART sensor, may need USB-Serial adapter'
                },
                'HC_SR04': {
                    'pins': {'trigger': 18, 'echo': 24},
                    'power': '5V',
                    'notes': 'Echo pin may need voltage divider for 3.3V compatibility'
                }
            },
            'setup_commands': [
                'sudo raspi-config -> Interface Options -> Enable I2C',
                'sudo raspi-config -> Interface Options -> Enable SPI',
                'pip install RPi.GPIO Adafruit-DHT spidev smbus2 pyserial',
                'sudo usermod -a -G dialout $USER  # For UART access'
            ]
        }
        return requirements
    
    def force_sensor_reconnect(self, sensor_type: str = None) -> Dict[str, Any]:
        """Force reconnection of specific sensor or all sensors"""
        results = {}
        
        if sensor_type:
            if sensor_type in self.sensors:
                sensor = self.sensors[sensor_type]
                logger.info(f"🔄 Forcing reconnection of {sensor_type}")
                sensor.force_reconnect()
                results[sensor_type] = {
                    'reconnected': True,
                    'active': sensor.is_active,
                    'consecutive_failures_reset': sensor.consecutive_failed_reads == 0,
                    'hardware_type': 'REAL_SENSOR'
                }
            else:
                results[sensor_type] = {'error': 'Sensor not found', 'hardware_type': 'REAL_SENSOR'}
        else:
            # Reconnect all sensors
            logger.info("🔄 Forcing reconnection of ALL sensors")
            for sensor_type, sensor in self.sensors.items():
                sensor.force_reconnect()
                results[sensor_type] = {
                    'reconnected': True,
                    'active': sensor.is_active,
                    'consecutive_failures_reset': sensor.consecutive_failed_reads == 0,
                    'hardware_type': 'REAL_SENSOR'
                }
        
        return results
    
    def get_troubleshooting_info(self) -> Dict[str, Any]:
        """Get detailed troubleshooting information for real hardware"""
        troubleshooting = {
            'system_info': {
                'gpio_available': GPIO_AVAILABLE,
                'spi_available': SPI_AVAILABLE,
                'uptime_minutes': round((time.time() - self.diagnostics['startup_time']) / 60, 2),
                'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
                'hardware_mode': 'REAL_SENSORS_ONLY',
                'simulation': False
            },
            'sensor_details': {},
            'common_issues': [],
            'hardware_checks': []
        }
        
        for sensor_type, sensor in self.sensors.items():
            stats = self.diagnostics['sensor_stats'][sensor_type]
            total_attempts = stats['successful_reads'] + stats['failed_reads']
            success_rate = (stats['successful_reads'] / max(1, total_attempts)) * 100
            
            troubleshooting['sensor_details'][sensor_type] = {
                'current_status': 'active' if sensor.is_active else 'inactive',
                'consecutive_failures': sensor.consecutive_failed_reads,
                'max_failure_threshold': sensor.max_connection_failures,
                'total_activations': stats['total_activations'],
                'total_deactivations': stats['total_deactivations'],
                'success_rate': round(success_rate, 2),
                'last_reading_time': sensor.last_reading_time.isoformat() if sensor.last_reading_time else None,
                'hardware_type': 'REAL_SENSOR'
            }
            
            # Add connection info
            if hasattr(sensor, 'data_pin'):
                troubleshooting['sensor_details'][sensor_type]['connection'] = f"GPIO Pin {sensor.data_pin}"
            elif hasattr(sensor, 'digital_pin'):
                troubleshooting['sensor_details'][sensor_type]['connection'] = f"Digital: GPIO {sensor.digital_pin}"
            elif hasattr(sensor, 'i2c_address'):
                troubleshooting['sensor_details'][sensor_type]['connection'] = f"I2C Address: {hex(sensor.i2c_address)}"
            elif hasattr(sensor, 'uart_port'):
                troubleshooting['sensor_details'][sensor_type]['connection'] = f"UART: {sensor.uart_port}"
            
            # Identify potential issues
            if not sensor.is_active:
                if stats['total_activations'] == 0:
                    troubleshooting['common_issues'].append(f"❌ {sensor_type}: Never activated - check power and wiring")
                    troubleshooting['hardware_checks'].append(f"Verify {sensor_type} power supply and GPIO connections")
                elif stats['total_deactivations'] > 0:
                    troubleshooting['common_issues'].append(f"⚠️ {sensor_type}: Lost connection - possible loose wiring")
                    troubleshooting['hardware_checks'].append(f"Check {sensor_type} cable connections")
            
            if success_rate < 50 and total_attempts > 10:
                troubleshooting['common_issues'].append(f"📉 {sensor_type}: Low success rate ({success_rate:.1f}%) - hardware issue likely")
                troubleshooting['hardware_checks'].append(f"Test {sensor_type} with multimeter/oscilloscope")
            
            # Sensor-specific checks
            if sensor_type == 'air_quality' and hasattr(sensor, 'is_warmed_up') and not sensor.is_warmed_up():
                troubleshooting['common_issues'].append(f"🔥 {sensor_type}: Still warming up (needs 3 minutes)")
            
            if sensor_type == 'light_sensor' and not sensor.is_active:
                troubleshooting['hardware_checks'].append("Check I2C is enabled: sudo raspi-config -> Interface Options -> I2C")
            
            if sensor_type == 'motion_radar' and not sensor.is_active:
                troubleshooting['hardware_checks'].append("Check UART permissions: sudo usermod -a -G dialout $USER")
        
        return troubleshooting
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            logger.info("🧹 Cleaning up sensor resources...")
            
            # Close serial connections
            for sensor in self.sensors.values():
                if hasattr(sensor, 'serial') and sensor.serial:
                    sensor.serial.close()
                    logger.debug(f"Closed serial connection for {sensor.sensor_id}")
                
                if hasattr(sensor, 'spi') and sensor.spi:
                    sensor.spi.close()
                    logger.debug(f"Closed SPI connection for {sensor.sensor_id}")
                
                if hasattr(sensor, 'bus') and sensor.bus:
                    sensor.bus.close()
                    logger.debug(f"Closed I2C bus for {sensor.sensor_id}")
            
            # Clean up GPIO
            if GPIO_AVAILABLE:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                logger.info("✅ GPIO cleaned up successfully")
                
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
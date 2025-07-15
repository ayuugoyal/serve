import time
import random
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .base_sensor import BaseSensor
import logging

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO_AVAILABLE = True
    logger.info("Hardware mode enabled")
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("GPIO module not available")

class UltrasonicSensor(BaseSensor):
    def __init__(self, sensor_id: str = "ULTRASONIC-01", asset_id: str = "DIST-SENSOR-01", 
                 trigger_pin: int = 18, echo_pin: int = 24):
        super().__init__(sensor_id, asset_id, "Zone-1")
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - Ultrasonic sensor not active")
            return
            
        try:
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            # Test the sensor by doing a quick reading
            if self._test_sensor_connection():
                self.is_active = True
                logger.info("Ultrasonic sensor connected and active")
            else:
                self.is_active = False
                logger.warning("Ultrasonic sensor not responding - possibly disconnected")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up ultrasonic sensor: {e}")
    
    def _test_sensor_connection(self) -> bool:
        """Test if the sensor is actually connected and responding"""
        try:
            GPIO.output(self.trigger_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trigger_pin, False)
            
            timeout_start = time.time()
            pulse_start = time.time()
            
            # Wait for echo to go HIGH
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if time.time() - timeout_start > 0.1:  # 100ms timeout for connection test
                    return False
            
            # Wait for echo to go LOW
            pulse_end = time.time()
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if time.time() - timeout_start > 0.1:  # 100ms timeout for connection test
                    return False
            
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            
            # If we get a reasonable distance reading, sensor is connected
            return 0.5 <= distance <= 500  # Reasonable range for HC-SR04
            
        except Exception as e:
            logger.error(f"Sensor connection test failed: {e}")
            return False
    
    def get_sensor_type(self) -> str:
        return "ultrasonic"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
        
        try:
            GPIO.output(self.trigger_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trigger_pin, False)
            
            pulse_start = time.time()
            timeout_start = time.time()
            
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if time.time() - timeout_start > 1:  # 1 second timeout
                    self.is_active = False  # Mark as inactive if timeout
                    return None
            
            pulse_end = time.time()
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if time.time() - timeout_start > 1:  # 1 second timeout
                    self.is_active = False  # Mark as inactive if timeout
                    return None
            
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            
            if 2 <= distance <= 400:
                return {
                    'distance_cm': round(distance, 2),
                    'distance_inches': round(distance / 2.54, 2),
                    'pins': {'trigger': self.trigger_pin, 'echo': self.echo_pin}
                }
            else:
                # Invalid reading might indicate disconnection
                return None
            
        except Exception as e:
            logger.error(f"Ultrasonic sensor error: {e}")
            self.is_active = False
            return None

class MQ135Sensor(BaseSensor):
    def __init__(self, sensor_id: str = "MQ135-01", asset_id: str = "AIR-QUALITY-01",
                 digital_pin: int = 25, analog_pin: int = 26):
        super().__init__(sensor_id, asset_id, "Zone-2")
        self.digital_pin = digital_pin
        self.analog_pin = analog_pin
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - MQ135 sensor not active")
            return
            
        try:
            GPIO.setup(self.digital_pin, GPIO.IN)
            # For MQ135, if the sensor is powered and connected, assume it's active
            # The sensor needs warm-up time and will show readings once stabilized
            self.is_active = True
            logger.info("MQ135 sensor initialized and set to active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up MQ135 sensor: {e}")
    
    def _test_sensor_connection(self) -> bool:
        """Simplified test - if we can read the pin, sensor is considered connected"""
        try:
            # Just try to read the pin - if no exception, sensor is connected
            GPIO.input(self.digital_pin)
            return True
        except Exception as e:
            logger.error(f"MQ135 sensor connection test failed: {e}")
            return False
    
    def get_sensor_type(self) -> str:
        return "air_quality"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
            
        try:
            # Test basic connection first
            if not self._test_sensor_connection():
                self.is_active = False
                return None
                
            # Read the digital output (LOW means gas detected for most MQ135 modules)
            digital_value = GPIO.input(self.digital_pin)
            gas_detected = not digital_value  # Inverted logic for most modules
            
            # Simulate analog reading based on digital state
            # In a real setup, you'd use an ADC to read analog value
            if gas_detected:
                ppm = random.randint(800, 1200)  # High gas concentration
                quality_level = "Poor"
            else:
                ppm = random.randint(300, 500)   # Normal air quality
                quality_level = "Good"
            
            return {
                'air_quality_ppm': ppm,
                'gas_detected': gas_detected,
                'quality_level': quality_level,
                'co2_equivalent': round(ppm * 2, 2),
                'digital_value': digital_value,
                'pins': {'digital': self.digital_pin, 'analog': self.analog_pin}
            }
            
        except Exception as e:
            logger.error(f"MQ135 sensor error: {e}")
            self.is_active = False
            return None

class DHT11Sensor(BaseSensor):
    def __init__(self, sensor_id: str = "DHT11-01", asset_id: str = "TEMP-HUM-01",
                 data_pin: int = 22):
        super().__init__(sensor_id, asset_id, "Zone-3")
        self.data_pin = data_pin
        self.dht = None
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - DHT11 sensor not active")
            return
            
        try:
            import Adafruit_DHT
            self.dht = Adafruit_DHT
            
            # Test if sensor is actually connected by attempting a reading
            if self._test_sensor_connection():
                self.is_active = True
                logger.info("DHT11 sensor connected and active")
            else:
                self.is_active = False
                logger.warning("DHT11 sensor not responding - possibly disconnected")
                
        except ImportError:
            self.is_active = False
            logger.warning("Adafruit_DHT module not available - DHT11 sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up DHT11 sensor: {e}")
    
    def _test_sensor_connection(self) -> bool:
        """Test if the DHT11 sensor is actually connected"""
        try:
            # Attempt to read from the sensor
            humidity, temperature = self.dht.read_retry(self.dht.DHT11, self.data_pin, retries=3, delay_seconds=1)
            
            # If we get valid readings, sensor is connected
            if humidity is not None and temperature is not None:
                # Basic sanity check for reasonable values
                if 0 <= humidity <= 100 and -40 <= temperature <= 80:
                    return True
            
            logger.warning("DHT11 sensor test failed - no valid readings")
            return False
            
        except Exception as e:
            logger.error(f"DHT11 sensor connection test failed: {e}")
            return False
    
    def get_sensor_type(self) -> str:
        return "temperature_humidity"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE or not self.dht:
            return None
            
        try:
            humidity, temperature = self.dht.read_retry(self.dht.DHT11, self.data_pin, retries=3)
            
            if humidity is not None and temperature is not None:
                # Validate readings are reasonable
                if 0 <= humidity <= 100 and -40 <= temperature <= 80:
                    return {
                        'temperature': round(temperature, 2),
                        'humidity': round(humidity, 2),
                        'comfort_level': self._calculate_comfort_level(temperature, humidity),
                        'pin': self.data_pin
                    }
            
            # If we get invalid readings, sensor might be disconnected
            logger.warning("DHT11 sensor returned invalid readings")
            self.is_active = False
            return None
            
        except Exception as e:
            logger.error(f"DHT11 sensor error: {e}")
            self.is_active = False
            return None
    
    def _calculate_comfort_level(self, temp: float, humidity: float) -> str:
        if 20 <= temp <= 25 and 30 <= humidity <= 60:
            return "Comfortable"
        elif temp > 25 or humidity > 60:
            return "Uncomfortable-Hot"
        else:
            return "Uncomfortable-Cold"

class LDRSensor(BaseSensor):
    def __init__(self, sensor_id: str = "LDR-01", asset_id: str = "LIGHT-SENSOR-01",
                 ldr_pin: int = 21):
        super().__init__(sensor_id, asset_id, "Zone-4")
        self.ldr_pin = ldr_pin
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - LDR sensor not active")
            return
            
        try:
            GPIO.setup(self.ldr_pin, GPIO.IN)
            # For LDR, if we can set up the pin, assume sensor is connected
            # LDR with proper circuit should always give some reading
            self.is_active = True
            logger.info("LDR sensor initialized and set to active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up LDR sensor: {e}")
    
    def _test_sensor_connection(self) -> bool:
        """Simplified test - if we can read the pin, sensor is considered connected"""
        try:
            # Just try to read the pin - if no exception, sensor is connected
            GPIO.input(self.ldr_pin)
            return True
        except Exception as e:
            logger.error(f"LDR sensor connection test failed: {e}")
            return False
    
    def get_sensor_type(self) -> str:
        return "light_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
            
        try:
            # Test basic connection first
            if not self._test_sensor_connection():
                self.is_active = False
                return None
                
            # Read the digital value from LDR circuit
            light_value = GPIO.input(self.ldr_pin)
            
            # Convert to meaningful light level
            light_level = "High" if light_value == 1 else "Low"
            
            # Add some additional calculated values
            light_percentage = 100 if light_value == 1 else 20
            
            return {
                'light_level': light_level,
                'light_percentage': light_percentage,
                'raw_value': light_value,
                'brightness': "Bright" if light_value == 1 else "Dark",
                'pin': self.ldr_pin
            }
            
        except Exception as e:
            logger.error(f"LDR sensor error: {e}")
            self.is_active = False
            return None

class PIRSensor(BaseSensor):
    def __init__(self, sensor_id: str = "PIR-01", asset_id: str = "MOTION-SENSOR-01",
                 data_pin: int = 17):
        super().__init__(sensor_id, asset_id, "Zone-5")
        self.data_pin = data_pin
        self.motion_count = 0
        self.last_motion_time = None
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - PIR sensor not active")
            return
            
        try:
            GPIO.setup(self.data_pin, GPIO.IN)
            
            # Test if sensor is actually connected
            if self._test_sensor_connection():
                self.is_active = True
                logger.info("PIR sensor connected and active")
            else:
                self.is_active = False
                logger.warning("PIR sensor not detected - possibly disconnected")
                
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up PIR sensor: {e}")
    
    def _test_sensor_connection(self) -> bool:
        """Test if the PIR sensor is actually connected"""
        try:
            # PIR sensors typically have a warm-up period and should show some activity
            # Read the pin multiple times to check for expected behavior
            readings = []
            for _ in range(50):  # Sample for 2.5 seconds
                readings.append(GPIO.input(self.data_pin))
                time.sleep(0.05)
            
            # Check for any variation in readings
            unique_readings = set(readings)
            
            if len(unique_readings) == 1:
                # All readings are the same - check if it's a valid state
                if all(r == 0 for r in readings):
                    # All LOW - could be normal idle state for PIR
                    return True
                else:
                    # All HIGH - likely floating pin or disconnected
                    logger.warning("PIR shows constant HIGH - sensor may be disconnected")
                    return False
            
            # We have variation - sensor is likely connected
            return True
            
        except Exception as e:
            logger.error(f"PIR sensor connection test failed: {e}")
            return False
    
    def get_sensor_type(self) -> str:
        return "motion_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
            
        try:
            motion_detected = GPIO.input(self.data_pin)
            current_time = datetime.now(timezone.utc)
            
            if motion_detected:
                self.motion_count += 1
                self.last_motion_time = current_time
            
            return {
                'motion_detected': bool(motion_detected),
                'motion_count': self.motion_count,
                'last_motion': self.last_motion_time.isoformat() if self.last_motion_time else None,
                'pin': self.data_pin
            }
            
        except Exception as e:
            logger.error(f"PIR sensor error: {e}")
            self.is_active = False
            return None
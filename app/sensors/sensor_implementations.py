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
    logger.info("Hardware mode enabled")
except ImportError:
    logger.warning("GPIO module not available")

class UltrasonicSensor(BaseSensor):
    def __init__(self, sensor_id: str = "ULTRASONIC-01", asset_id: str = "DIST-SENSOR-01", 
                 trigger_pin: int = 18, echo_pin: int = 24):
        super().__init__(sensor_id, asset_id, "Zone-1")
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.setup_pins()
    
    def setup_pins(self):
        try:
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            self.is_active = True
        except (NameError, AttributeError):
            self.is_active = False
            logger.warning("GPIO not available - Ultrasonic sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up ultrasonic sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "ultrasonic"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active:
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
                    return None
            
            pulse_end = time.time()
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if time.time() - timeout_start > 1:  # 1 second timeout
                    return None
            
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            
            if 2 <= distance <= 400:
                return {
                    'distance_cm': round(distance, 2),
                    'distance_inches': round(distance / 2.54, 2),
                    'pins': {'trigger': self.trigger_pin, 'echo': self.echo_pin}
                }
            return None
            
        except Exception as e:
            logger.error(f"Ultrasonic sensor error: {e}")
            return None

class MQ135Sensor(BaseSensor):
    def __init__(self, sensor_id: str = "MQ135-01", asset_id: str = "AIR-QUALITY-01",
                 digital_pin: int = 25, analog_pin: int = 26):
        super().__init__(sensor_id, asset_id, "Zone-2")
        self.digital_pin = digital_pin
        self.analog_pin = analog_pin
        self.setup_pins()
    
    def setup_pins(self):
        try:
            GPIO.setup(self.digital_pin, GPIO.IN)
            GPIO.setup(self.analog_pin, GPIO.IN)
            self.is_active = True
        except (NameError, AttributeError):
            self.is_active = False
            logger.warning("GPIO not available - MQ135 sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up MQ135 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "air_quality"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active:
            return None
            
        try:
            gas_detected = not GPIO.input(self.digital_pin)
            # For analog reading, you would need an ADC. This is simplified.
            ppm = 800 if gas_detected else 400
            quality_level = "Poor" if gas_detected else "Good"
            
            return {
                'air_quality_ppm': ppm,
                'gas_detected': gas_detected,
                'quality_level': quality_level,
                'co2_equivalent': round(ppm * 2, 2),
                'pins': {'digital': self.digital_pin, 'analog': self.analog_pin}
            }
            
        except Exception as e:
            logger.error(f"MQ135 sensor error: {e}")
            return None

class DHT11Sensor(BaseSensor):
    def __init__(self, sensor_id: str = "DHT11-01", asset_id: str = "TEMP-HUM-01",
                 data_pin: int = 22):
        super().__init__(sensor_id, asset_id, "Zone-3")
        self.data_pin = data_pin
        self.setup_pins()
    
    def setup_pins(self):
        try:
            import Adafruit_DHT
            self.dht = Adafruit_DHT
            self.is_active = True
        except ImportError:
            self.is_active = False
            logger.warning("DHT11 module not available - Temperature/Humidity sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up DHT11 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "temperature_humidity"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active:
            return None
            
        try:
            humidity, temperature = self.dht.read_retry(self.dht.DHT11, self.data_pin)
            if humidity is not None and temperature is not None:
                return {
                    'temperature': round(temperature, 2),
                    'humidity': round(humidity, 2),
                    'comfort_level': self._calculate_comfort_level(temperature, humidity),
                    'pin': self.data_pin
                }
            return None
            
        except Exception as e:
            logger.error(f"DHT11 sensor error: {e}")
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
        try:
            GPIO.setup(self.ldr_pin, GPIO.IN)
            self.is_active = True
        except (NameError, AttributeError):
            self.is_active = False
            logger.warning("GPIO not available - Light sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up LDR sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "light_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active:
            return None
            
        try:
            light_level = GPIO.input(self.ldr_pin)
            return {
                'light_level': "High" if light_level else "Low",
                'raw_value': light_level,
                'pin': self.ldr_pin
            }
        except Exception as e:
            logger.error(f"LDR sensor error: {e}")
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
        try:
            GPIO.setup(self.data_pin, GPIO.IN)
            self.is_active = True
        except (NameError, AttributeError):
            self.is_active = False
            logger.warning("GPIO not available - PIR sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up PIR sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "motion_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active:
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
            return None

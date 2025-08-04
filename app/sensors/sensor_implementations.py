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
            GPIO.output(self.trigger_pin, False)
            time.sleep(0.1)  # Let sensor settle
            self.is_active = True
            logger.info("Ultrasonic sensor pins configured")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up ultrasonic sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "ultrasonic"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
        
        try:
            # Ensure trigger is LOW
            GPIO.output(self.trigger_pin, False)
            time.sleep(0.000002)  # 2μs
            
            # Send 10μs pulse
            GPIO.output(self.trigger_pin, True)
            time.sleep(0.00001)  # 10μs
            GPIO.output(self.trigger_pin, False)
            
            # Wait for echo start with timeout
            timeout_start = time.time()
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if time.time() - timeout_start > 0.5:  # 500ms timeout
                    logger.debug("Ultrasonic timeout waiting for echo start")
                    return None
            
            # Wait for echo end with timeout
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if time.time() - timeout_start > 0.5:  # 500ms timeout
                    logger.debug("Ultrasonic timeout waiting for echo end")
                    return None
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            
            # Validate distance reading
            if 2 <= distance <= 400:  # HC-SR04 valid range
                return {
                    'distance_cm': round(distance, 2),
                    'distance_inches': round(distance / 2.54, 2),
                    'pulse_duration_us': round(pulse_duration * 1000000, 2),
                    'pins': {'trigger': self.trigger_pin, 'echo': self.echo_pin}
                }
            else:
                logger.debug(f"Ultrasonic invalid distance: {distance}cm")
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
        self.warmup_time = 60  # MQ135 needs 60 seconds warmup
        self.start_time = time.time()
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - MQ135 sensor not active")
            return
            
        try:
            GPIO.setup(self.digital_pin, GPIO.IN)
            self.is_active = True
            logger.info("MQ135 sensor initialized - warming up...")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up MQ135 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "air_quality"
    
    def is_warmed_up(self) -> bool:
        return (time.time() - self.start_time) >= self.warmup_time
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
            
        try:
            if not self.is_warmed_up():
                warmup_remaining = self.warmup_time - (time.time() - self.start_time)
                return {
                    'warming_up': True,
                    'warmup_remaining_seconds': int(warmup_remaining),
                    'digital_value': GPIO.input(self.digital_pin),
                    'pins': {'digital': self.digital_pin, 'analog': self.analog_pin}
                }
            
            # Read the digital output
            digital_value = GPIO.input(self.digital_pin)
            gas_detected = not digital_value  # Most MQ135 modules are active LOW
            
            # For real analog reading, you would need an ADC like MCP3008
            # This is a placeholder - replace with actual ADC reading
            # Example with MCP3008:
            # import spidev
            # spi = spidev.SpiDev()
            # spi.open(0, 0)
            # analog_value = spi.xfer2([1, (8 + self.analog_pin) << 4, 0])[2]
            
            return {
                'gas_detected': gas_detected,
                'digital_value': digital_value,
                'sensor_warmed_up': True,
                'pins': {'digital': self.digital_pin, 'analog': self.analog_pin},
                'note': 'For PPM readings, connect to ADC (MCP3008) and implement analog conversion'
            }
            
        except Exception as e:
            logger.error(f"MQ135 sensor error: {e}")
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
            self.is_active = True
            logger.info("DHT11 sensor initialized")
        except ImportError:
            self.is_active = False
            logger.warning("Adafruit_DHT module not available - DHT11 sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up DHT11 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "temperature_humidity"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE or not self.dht:
            return None
            
        try:
            # DHT11 readings can be unreliable, so we retry with delays
            humidity, temperature = self.dht.read_retry(
                self.dht.DHT11, 
                self.data_pin, 
                retries=3, 
                delay_seconds=2
            )
            
            if humidity is not None and temperature is not None:
                # Validate readings are reasonable for DHT11
                if 20 <= humidity <= 95 and -20 <= temperature <= 60:
                    return {
                        'temperature_celsius': round(temperature, 1),
                        'temperature_fahrenheit': round((temperature * 9/5) + 32, 1),
                        'humidity_percent': round(humidity, 1),
                        'comfort_level': self._calculate_comfort_level(temperature, humidity),
                        'dew_point': round(self._calculate_dew_point(temperature, humidity), 1),
                        'pin': self.data_pin
                    }
                else:
                    logger.debug(f"DHT11 readings out of range: T={temperature}, H={humidity}")
                    return None
            else:
                logger.debug("DHT11 returned None values")
                return None
            
        except Exception as e:
            logger.error(f"DHT11 sensor error: {e}")
            return None
    
    def _calculate_comfort_level(self, temp: float, humidity: float) -> str:
        if 20 <= temp <= 25 and 40 <= humidity <= 60:
            return "Comfortable"
        elif temp > 25 or humidity > 60:
            return "Too Hot/Humid"
        elif temp < 20 or humidity < 40:
            return "Too Cold/Dry"
        else:
            return "Borderline"
    
    def _calculate_dew_point(self, temp: float, humidity: float) -> float:
        # Simplified dew point calculation
        import math
        a = 17.27
        b = 237.7
        alpha = ((a * temp) / (b + temp)) + math.log(humidity / 100.0)
        return (b * alpha) / (a - alpha)

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
            self.is_active = True
            logger.info("LDR sensor initialized")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up LDR sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "light_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
            
        try:
            # For digital LDR with comparator circuit
            light_digital = GPIO.input(self.ldr_pin)
            
            # If you want analog readings, you need an ADC
            # For now, providing digital interpretation
            light_detected = bool(light_digital)
            
            return {
                'light_detected': light_detected,
                'light_level': "Bright" if light_detected else "Dark",
                'digital_value': light_digital,
                'pin': self.ldr_pin,
                'note': 'For analog readings, connect LDR to ADC (MCP3008)'
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
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - PIR sensor not active")
            return
            
        try:
            GPIO.setup(self.data_pin, GPIO.IN)
            # PIR sensors need settling time
            time.sleep(2)
            self.is_active = True
            logger.info("PIR sensor initialized")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up PIR sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "motion_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
            
        try:
            motion_detected = bool(GPIO.input(self.data_pin))
            current_time = datetime.now(timezone.utc)
            
            if motion_detected:
                self.motion_count += 1
                self.last_motion_time = current_time
            
            # Calculate time since last motion
            time_since_motion = None
            if self.last_motion_time:
                time_since_motion = int((current_time - self.last_motion_time).total_seconds())
            
            return {
                'motion_detected': motion_detected,
                'motion_count': self.motion_count,
                'last_motion_time': self.last_motion_time.isoformat() if self.last_motion_time else None,
                'time_since_motion_seconds': time_since_motion,
                'pin': self.data_pin
            }
            
        except Exception as e:
            logger.error(f"PIR sensor error: {e}")
            return None
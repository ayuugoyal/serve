import time
import random
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .base_sensor import BaseSensor

logger = logging.getLogger(__name__)

# Check if running on Raspberry Pi
try:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
    SIMULATION_MODE = False
    logger.info("Real hardware mode enabled")
except ImportError:
    SIMULATION_MODE = True
    logger.warning("Running in simulation mode")

class UltrasonicSensor(BaseSensor):
    def __init__(self, sensor_id: str = "ULTRASONIC-01", asset_id: str = "DIST-SENSOR-01", 
                 trigger_pin: int = 18, echo_pin: int = 24):
        super().__init__(sensor_id, asset_id, "Zone-1")
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.setup_pins()
    
    def setup_pins(self):
        if not SIMULATION_MODE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.trigger_pin, GPIO.OUT)
                GPIO.setup(self.echo_pin, GPIO.IN)
                GPIO.output(self.trigger_pin, False)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error setting up ultrasonic pins: {e}")
    
    def get_sensor_type(self) -> str:
        return "ultrasonic"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if SIMULATION_MODE:
            # Simulate distance reading
            distance = random.uniform(10, 200)
            return {
                'distance_cm': round(distance, 2),
                'distance_inches': round(distance / 2.54, 2),
                'pins': {'trigger': self.trigger_pin, 'echo': self.echo_pin}
            }
        
        try:
            GPIO.output(self.trigger_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trigger_pin, False)
            
            timeout_start = time.time()
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if pulse_start - timeout_start > 0.05:
                    return None
            
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if pulse_end - timeout_start > 0.05:
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
        if not SIMULATION_MODE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.digital_pin, GPIO.IN)
            except Exception as e:
                logger.error(f"Error setting up MQ135 pins: {e}")
    
    def get_sensor_type(self) -> str:
        return "air_quality"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if SIMULATION_MODE:
            # Simulate air quality reading
            ppm = random.uniform(300, 1500)
            gas_detected = ppm > 800
            quality_level = "Good" if ppm < 500 else "Poor" if ppm < 1000 else "Dangerous"
            
            return {
                'air_quality_ppm': round(ppm, 2),
                'gas_detected': gas_detected,
                'quality_level': quality_level,
                'co2_equivalent': round(ppm * 2, 2),
                'pins': {'digital': self.digital_pin, 'analog': self.analog_pin}
            }
        
        try:
            gas_detected = not GPIO.input(self.digital_pin)
            # Simulate analog reading for now
            ppm = random.uniform(300, 1500) if gas_detected else random.uniform(300, 800)
            quality_level = "Good" if ppm < 500 else "Poor" if ppm < 1000 else "Dangerous"
            
            return {
                'air_quality_ppm': round(ppm, 2),
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
    
    def get_sensor_type(self) -> str:
        return "temperature_humidity"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if SIMULATION_MODE:
            # Simulate temperature and humidity
            temperature = random.uniform(18, 35)
            humidity = random.uniform(30, 80)
            
            return {
                'temperature_celsius': round(temperature, 2),
                'temperature_fahrenheit': round((temperature * 9/5) + 32, 2),
                'humidity_percent': round(humidity, 2),
                'pins': {'data': self.data_pin}
            }
        
        try:
            humidity, temperature = Adafruit_DHT.read_retry(
                Adafruit_DHT.DHT11, self.data_pin, retries=1, delay_seconds=0.5
            )
            
            if humidity is not None and temperature is not None:
                if 20 <= humidity <= 95 and 0 <= temperature <= 60:
                    return {
                        'temperature_celsius': round(temperature, 2),
                        'temperature_fahrenheit': round((temperature * 9/5) + 32, 2),
                        'humidity_percent': round(humidity, 2),
                        'pins': {'data': self.data_pin}
                    }
            return None
            
        except Exception as e:
            logger.error(f"DHT11 sensor error: {e}")
            return None

class LDRSensor(BaseSensor):
    def __init__(self, sensor_id: str = "LDR-01", asset_id: str = "LIGHT-SENSOR-01",
                 ldr_pin: int = 21):
        super().__init__(sensor_id, asset_id, "Zone-4")
        self.ldr_pin = ldr_pin
    
    def get_sensor_type(self) -> str:
        return "light_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if SIMULATION_MODE:
            # Simulate light reading
            light_percentage = random.uniform(0, 100)
            light_condition = "Dark" if light_percentage < 20 else "Normal" if light_percentage < 80 else "Very Bright"
            
            return {
                'light_level_raw': int(random.uniform(1000, 100000)),
                'light_percentage': round(light_percentage, 2),
                'light_condition': light_condition,
                'pins': {'ldr': self.ldr_pin}
            }
        
        try:
            # Implement RC time measurement for LDR
            count = 0
            GPIO.setup(self.ldr_pin, GPIO.OUT)
            GPIO.output(self.ldr_pin, GPIO.LOW)
            time.sleep(0.1)
            
            GPIO.setup(self.ldr_pin, GPIO.IN)
            start_time = time.time()
            
            while GPIO.input(self.ldr_pin) == GPIO.LOW:
                count += 1
                if count > 1000000 or (time.time() - start_time) > 2:
                    break
            
            if count > 0:
                max_dark = 1000000
                min_bright = 1000
                
                if count >= max_dark:
                    percentage = 0
                elif count <= min_bright:
                    percentage = 100
                else:
                    percentage = 100 * (1 - ((count - min_bright) / (max_dark - min_bright)))
                    percentage = max(0, min(100, percentage))
                
                light_condition = "Dark" if percentage < 20 else "Normal" if percentage < 80 else "Very Bright"
                
                return {
                    'light_level_raw': count,
                    'light_percentage': round(percentage, 2),
                    'light_condition': light_condition,
                    'pins': {'ldr': self.ldr_pin}
                }
            return None
            
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
        if not SIMULATION_MODE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.data_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                time.sleep(2)  # Allow sensor to stabilize
            except Exception as e:
                logger.error(f"Error setting up PIR pins: {e}")
    
    def get_sensor_type(self) -> str:
        return "motion_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if SIMULATION_MODE:
            # Simulate motion detection
            motion_detected = random.choice([True, False, False, False])  # 25% chance
            if motion_detected:
                self.motion_count += 1
                self.last_motion_time = datetime.now(timezone.utc)
            
            time_since_motion = None
            if self.last_motion_time:
                time_since_motion = (datetime.now(timezone.utc) - self.last_motion_time).total_seconds()
            
            return {
                'motion_detected': motion_detected,
                'motion_count': self.motion_count,
                'last_motion_time': self.last_motion_time.isoformat() if self.last_motion_time else None,
                'time_since_motion_seconds': round(time_since_motion, 2) if time_since_motion else None,
                'pins': {'data': self.data_pin}
            }
        
        try:
            motion = GPIO.input(self.data_pin)
            current_time = datetime.now(timezone.utc)
            
            if motion:
                self.motion_count += 1
                self.last_motion_time = current_time
            
            time_since_motion = None
            if self.last_motion_time:
                time_since_motion = (current_time - self.last_motion_time).total_seconds()
            
            return {
                'motion_detected': bool(motion),
                'motion_count': self.motion_count,
                'last_motion_time': self.last_motion_time.isoformat() if self.last_motion_time else None,
                'time_since_motion_seconds': round(time_since_motion, 2) if time_since_motion else None,
                'pins': {'data': self.data_pin}
            }
            
        except Exception as e:
            logger.error(f"PIR sensor error: {e}")
            return None

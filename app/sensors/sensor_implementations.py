import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .base_sensor import BaseSensor

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO_AVAILABLE = True
    logger.info("Hardware mode enabled")
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("GPIO module not available")

try:
    import spidev
    SPI_AVAILABLE = True
except ImportError:
    SPI_AVAILABLE = False
    logger.warning("SPI module not available for ADC readings")

class DHT22Sensor(BaseSensor):
    """DHT22/AM2302 Temperature and Humidity Sensor"""
    def __init__(self, sensor_id: str = "DHT22-01", asset_id: str = "TEMP-HUM-01",
                 data_pin: int = 22):
        super().__init__(sensor_id, asset_id, "Zone-1")
        self.data_pin = data_pin
        self.dht = None
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - DHT22 sensor not active")
            return
            
        try:
            import Adafruit_DHT
            self.dht = Adafruit_DHT
            self.is_active = True
            logger.info("DHT22 sensor initialized")
        except ImportError:
            self.is_active = False
            logger.warning("Adafruit_DHT module not available - DHT22 sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up DHT22 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "temperature_humidity"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE or not self.dht:
            return None
            
        try:
            humidity, temperature = self.dht.read_retry(
                self.dht.DHT22, 
                self.data_pin, 
                retries=3, 
                delay_seconds=2
            )
            
            if humidity is not None and temperature is not None:
                # DHT22 has better range than DHT11: -40 to 80°C, 0-100% RH
                if 0 <= humidity <= 100 and -40 <= temperature <= 80:
                    return {
                        'temperature_celsius': round(temperature, 2),
                        'temperature_fahrenheit': round((temperature * 9/5) + 32, 2),
                        'humidity_percent': round(humidity, 2),
                        'comfort_level': self._calculate_comfort_level(temperature, humidity),
                        'dew_point': round(self._calculate_dew_point(temperature, humidity), 2),
                        'heat_index': round(self._calculate_heat_index(temperature, humidity), 2),
                        'pin': self.data_pin,
                        'sensor_model': 'DHT22/AM2302'
                    }
                else:
                    logger.debug(f"DHT22 readings out of range: T={temperature}, H={humidity}")
                    return None
            else:
                logger.debug("DHT22 returned None values")
                return None
            
        except Exception as e:
            logger.error(f"DHT22 sensor error: {e}")
            return None
    
    def _calculate_comfort_level(self, temp: float, humidity: float) -> str:
        if 20 <= temp <= 26 and 40 <= humidity <= 60:
            return "Comfortable"
        elif temp > 26 or humidity > 70:
            return "Too Hot/Humid"
        elif temp < 18 or humidity < 30:
            return "Too Cold/Dry"
        else:
            return "Moderate"
    
    def _calculate_dew_point(self, temp: float, humidity: float) -> float:
        import math
        a = 17.27
        b = 237.7
        if humidity <= 0:
            return temp
        alpha = ((a * temp) / (b + temp)) + math.log(humidity / 100.0)
        return (b * alpha) / (a - alpha)
    
    def _calculate_heat_index(self, temp: float, humidity: float) -> float:
        """Calculate heat index in Celsius"""
        # Convert to Fahrenheit for calculation
        temp_f = (temp * 9/5) + 32
        
        if temp_f < 80 or humidity < 40:
            return temp  # Heat index not applicable
        
        # Heat index formula
        hi = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (humidity * 0.094))
        
        if hi > 79:
            # More complex formula for higher temperatures
            hi = -42.379 + 2.04901523 * temp_f + 10.14333127 * humidity
            hi -= 0.22475541 * temp_f * humidity - 6.83783e-3 * temp_f**2
            hi -= 5.481717e-2 * humidity**2 + 1.22874e-3 * temp_f**2 * humidity
            hi += 8.5282e-4 * temp_f * humidity**2 - 1.99e-6 * temp_f**2 * humidity**2
        
        # Convert back to Celsius
        return (hi - 32) * 5/9

class MQ135Sensor(BaseSensor):
    """MQ135 Air Quality/Gas Detector Sensor with ADC support"""
    def __init__(self, sensor_id: str = "MQ135-01", asset_id: str = "MCN-04",
                 digital_pin: int = 25, spi_channel: int = 0, adc_channel: int = 0):
        super().__init__(sensor_id, asset_id, "Zone-2")
        self.digital_pin = digital_pin
        self.spi_channel = spi_channel
        self.adc_channel = adc_channel
        self.warmup_time = 180  # MQ135 needs 3 minutes warmup
        self.start_time = time.time()
        self.spi = None
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - MQ135 sensor not active")
            return
            
        try:
            GPIO.setup(self.digital_pin, GPIO.IN)
            
            # Try to initialize SPI for analog readings
            if SPI_AVAILABLE:
                try:
                    import spidev
                    self.spi = spidev.SpiDev()
                    self.spi.open(0, self.spi_channel)
                    self.spi.max_speed_hz = 1000000
                    logger.info("MQ135 sensor initialized with SPI ADC support")
                except Exception as e:
                    logger.warning(f"SPI initialization failed: {e}")
                    logger.info("MQ135 sensor initialized (digital only)")
            
            self.is_active = True
            logger.info("MQ135 sensor warming up (3 minutes required)...")
            
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up MQ135 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "air_quality"
    
    def is_warmed_up(self) -> bool:
        return (time.time() - self.start_time) >= self.warmup_time
    
    def read_analog_value(self) -> Optional[int]:
        """Read analog value via SPI ADC (MCP3008)"""
        if not self.spi:
            return None
            
        try:
            # MCP3008 SPI protocol
            adc = self.spi.xfer2([1, (8 + self.adc_channel) << 4, 0])
            data = ((adc[1] & 3) << 8) + adc[2]
            return data
        except Exception as e:
            logger.error(f"Error reading MQ135 analog value: {e}")
            return None
    
    def calculate_ppm(self, analog_value: int) -> float:
        """Convert analog reading to approximate PPM"""
        if analog_value <= 0:
            return 0
        
        # MQ135 conversion (approximate - requires calibration for accuracy)
        voltage = (analog_value / 1024.0) * 3.3  # Assuming 3.3V reference
        rs_air = 76.63  # Rs in clean air (calibrate this value)
        r0 = 10.0  # Load resistance in KΩ
        
        # Calculate Rs/R0 ratio
        rs = ((3.3 - voltage) / voltage) * r0
        ratio = rs / rs_air
        
        # Convert to PPM (approximate formula for CO2/NH3/NOx)
        if ratio > 0:
            ppm = 116.6020682 * pow(ratio, -2.769034857)
            return max(0, min(ppm, 10000))  # Limit to reasonable range
        
        return 0
    
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
                    'pin': self.digital_pin,
                    'sensor_model': 'MQ135'
                }
            
            digital_value = GPIO.input(self.digital_pin)
            gas_detected = not digital_value  # Active LOW
            
            result = {
                'gas_detected': gas_detected,
                'digital_value': digital_value,
                'sensor_warmed_up': True,
                'pin': self.digital_pin,
                'sensor_model': 'MQ135'
            }
            
            # Add analog reading if available
            analog_value = self.read_analog_value()
            if analog_value is not None:
                ppm = self.calculate_ppm(analog_value)
                result.update({
                    'analog_value': analog_value,
                    'estimated_ppm': round(ppm, 2),
                    'voltage': round((analog_value / 1024.0) * 3.3, 3),
                    'air_quality': self._categorize_air_quality(ppm)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"MQ135 sensor error: {e}")
            return None
    
    def _categorize_air_quality(self, ppm: float) -> str:
        """Categorize air quality based on PPM levels"""
        if ppm < 400:
            return "Excellent"
        elif ppm < 1000:
            return "Good"
        elif ppm < 2000:
            return "Moderate"
        elif ppm < 5000:
            return "Poor"
        else:
            return "Hazardous"

class BH1750Sensor(BaseSensor):
    """GY-302 BH1750 Light Intensity Module (I2C)"""
    def __init__(self, sensor_id: str = "BH1750-01", asset_id: str = "LIGHT-SENSOR-01",
                 i2c_address: int = 0x23):
        super().__init__(sensor_id, asset_id, "Zone-3")
        self.i2c_address = i2c_address
        self.bus = None
        self.setup_pins()
    
    def setup_pins(self):
        try:
            import smbus2
            self.bus = smbus2.SMBus(1)  # I2C bus 1 on Raspberry Pi
            self.is_active = True
            logger.info("BH1750 light sensor initialized")
        except ImportError:
            self.is_active = False
            logger.warning("smbus2 not available - BH1750 sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up BH1750 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "light_sensor"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not self.bus:
            return None
            
        try:
            # BH1750 commands
            POWER_ON = 0x01
            CONTINUOUS_HIGH_RES_MODE = 0x10
            
            # Power on and set measurement mode
            self.bus.write_byte(self.i2c_address, POWER_ON)
            time.sleep(0.01)
            self.bus.write_byte(self.i2c_address, CONTINUOUS_HIGH_RES_MODE)
            time.sleep(0.18)  # Wait for measurement (120ms typical)
            
            # Read 2 bytes of data
            data = self.bus.read_i2c_block_data(self.i2c_address, 0x00, 2)
            
            # Convert to lux
            lux = (data[0] << 8 | data[1]) / 1.2
            
            return {
                'lux': round(lux, 2),
                'light_level': self._categorize_light_level(lux),
                'raw_data': data,
                'i2c_address': hex(self.i2c_address),
                'sensor_model': 'BH1750'
            }
            
        except Exception as e:
            logger.error(f"BH1750 sensor error: {e}")
            return None
    
    def _categorize_light_level(self, lux: float) -> str:
        """Categorize light levels"""
        if lux < 1:
            return "Very Dark"
        elif lux < 10:
            return "Dark"
        elif lux < 50:
            return "Dim"
        elif lux < 200:
            return "Normal Indoor"
        elif lux < 500:
            return "Bright Indoor"
        elif lux < 1000:
            return "Very Bright"
        else:
            return "Direct Sunlight"

class GP2Y1010AU0FSensor(BaseSensor):
    """PM2.5 GP2Y1010AU0F Dust/Smoke Particle Sensor"""
    def __init__(self, sensor_id: str = "GP2Y1010-01", asset_id: str = "DUST-SENSOR-01",
                 led_pin: int = 7, adc_channel: int = 1, spi_channel: int = 0):
        super().__init__(sensor_id, asset_id, "Zone-4")
        self.led_pin = led_pin
        self.adc_channel = adc_channel
        self.spi_channel = spi_channel
        self.spi = None
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - GP2Y1010AU0F sensor not active")
            return
            
        try:
            GPIO.setup(self.led_pin, GPIO.OUT)
            GPIO.output(self.led_pin, False)  # LED off initially
            
            if SPI_AVAILABLE:
                import spidev
                self.spi = spidev.SpiDev()
                self.spi.open(0, self.spi_channel)
                self.spi.max_speed_hz = 1000000
            
            self.is_active = True
            logger.info("GP2Y1010AU0F dust sensor initialized")
            
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up GP2Y1010AU0F sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "dust_sensor"
    
    def read_analog_value(self) -> Optional[int]:
        """Read analog value via SPI ADC"""
        if not self.spi:
            return None
            
        try:
            adc = self.spi.xfer2([1, (8 + self.adc_channel) << 4, 0])
            data = ((adc[1] & 3) << 8) + adc[2]
            return data
        except Exception as e:
            logger.error(f"Error reading dust sensor analog value: {e}")
            return None
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not GPIO_AVAILABLE:
            return None
            
        try:
            # Turn on LED and wait
            GPIO.output(self.led_pin, True)
            time.sleep(0.00028)  # 280μs pulse
            
            # Read analog value
            no_dust = self.read_analog_value()
            time.sleep(0.00004)  # 40μs
            
            # Turn off LED
            GPIO.output(self.led_pin, False)
            time.sleep(0.009680)  # 9.68ms
            
            if no_dust is None:
                return None
            
            # Convert to voltage
            voltage = (no_dust / 1024.0) * 5.0  # Assuming 5V reference
            
            # Calculate dust density (approximate formula)
            dust_voltage = voltage - 0.1  # Baseline voltage
            dust_density = 0
            
            if dust_voltage > 0:
                dust_density = dust_voltage * 400  # μg/m³
            
            return {
                'dust_density_ug_m3': round(max(0, dust_density), 2),
                'voltage': round(voltage, 3),
                'raw_adc': no_dust,
                'air_quality': self._categorize_dust_level(dust_density),
                'led_pin': self.led_pin,
                'sensor_model': 'GP2Y1010AU0F'
            }
            
        except Exception as e:
            logger.error(f"GP2Y1010AU0F sensor error: {e}")
            return None
    
    def _categorize_dust_level(self, dust_density: float) -> str:
        """Categorize dust/particle levels"""
        if dust_density < 12:
            return "Excellent"
        elif dust_density < 35:
            return "Good"
        elif dust_density < 55:
            return "Moderate"
        elif dust_density < 150:
            return "Unhealthy for Sensitive"
        elif dust_density < 250:
            return "Unhealthy"
        else:
            return "Hazardous"

class PiezoVibrationSensor(BaseSensor):
    """Grove Piezo Vibration Sensor"""
    def __init__(self, sensor_id: str = "PIEZO-01", asset_id: str = "VIBRATION-SENSOR-01",
                 analog_pin: int = 2, threshold: int = 100):
        super().__init__(sensor_id, asset_id, "Zone-5")
        self.analog_pin = analog_pin
        self.threshold = threshold
        self.spi = None
        self.vibration_count = 0
        self.last_vibration_time = None
        self.setup_pins()
    
    def setup_pins(self):
        try:
            if SPI_AVAILABLE:
                import spidev
                self.spi = spidev.SpiDev()
                self.spi.open(0, 0)
                self.spi.max_speed_hz = 1000000
                self.is_active = True
                logger.info("Piezo vibration sensor initialized")
            else:
                self.is_active = False
                logger.warning("SPI not available - Piezo sensor not active")
                
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up Piezo sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "vibration_sensor"
    
    def read_analog_value(self) -> Optional[int]:
        """Read analog value via SPI ADC"""
        if not self.spi:
            return None
            
        try:
            adc = self.spi.xfer2([1, (8 + self.analog_pin) << 4, 0])
            data = ((adc[1] & 3) << 8) + adc[2]
            return data
        except Exception as e:
            logger.error(f"Error reading vibration sensor: {e}")
            return None
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not self.spi:
            return None
            
        try:
            # Take multiple readings to detect vibration
            readings = []
            for _ in range(10):
                reading = self.read_analog_value()
                if reading is not None:
                    readings.append(reading)
                time.sleep(0.01)
            
            if not readings:
                return None
            
            avg_reading = sum(readings) / len(readings)
            max_reading = max(readings)
            min_reading = min(readings)
            vibration_amplitude = max_reading - min_reading
            
            # Detect vibration based on amplitude
            vibration_detected = vibration_amplitude > self.threshold
            current_time = datetime.now(timezone.utc)
            
            if vibration_detected:
                self.vibration_count += 1
                self.last_vibration_time = current_time
            
            # Calculate time since last vibration
            time_since_vibration = None
            if self.last_vibration_time:
                time_since_vibration = int((current_time - self.last_vibration_time).total_seconds())
            
            return {
                'vibration_detected': vibration_detected,
                'vibration_amplitude': vibration_amplitude,
                'vibration_count': self.vibration_count,
                'average_reading': round(avg_reading, 2),
                'max_reading': max_reading,
                'min_reading': min_reading,
                'threshold': self.threshold,
                'vibration_level': self._categorize_vibration_level(vibration_amplitude),
                'last_vibration_time': self.last_vibration_time.isoformat() if self.last_vibration_time else None,
                'time_since_vibration_seconds': time_since_vibration,
                'sensor_model': 'Grove Piezo'
            }
            
        except Exception as e:
            logger.error(f"Piezo vibration sensor error: {e}")
            return None
    
    def _categorize_vibration_level(self, amplitude: float) -> str:
        """Categorize vibration levels"""
        if amplitude < 50:
            return "No Vibration"
        elif amplitude < 150:
            return "Light Vibration"
        elif amplitude < 300:
            return "Moderate Vibration"
        elif amplitude < 500:
            return "Strong Vibration"
        else:
            return "Very Strong Vibration"

class HLK_LD2420Sensor(BaseSensor):
    """Hi-Link HLK-LD2420 24Ghz Human Body Motion Sensor"""
    def __init__(self, sensor_id: str = "LD2420-01", asset_id: str = "MOTION-RADAR-01",
                 uart_port: str = "/dev/ttyUSB0", baud_rate: int = 256000):
        super().__init__(sensor_id, asset_id, "Zone-6")
        self.uart_port = uart_port
        self.baud_rate = baud_rate
        self.serial = None
        self.motion_count = 0
        self.last_motion_time = None
        self.setup_serial()
    
    def setup_serial(self):
        try:
            import serial
            self.serial = serial.Serial(
                port=self.uart_port,
                baudrate=self.baud_rate,
                timeout=1
            )
            self.is_active = True
            logger.info(f"LD2420 radar sensor initialized on {self.uart_port}")
            
        except ImportError:
            self.is_active = False
            logger.warning("pyserial not available - LD2420 sensor not active")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up LD2420 sensor: {e}")
    
    def get_sensor_type(self) -> str:
        return "motion_radar"
    
    def read_sensor_data(self) -> Optional[Dict[str, Any]]:
        if not self.is_active or not self.serial:
            return None
            
        try:
            # Read data from serial port
            if self.serial.in_waiting > 0:
                data = self.serial.read(self.serial.in_waiting)
                
                # Parse HLK-LD2420 protocol (simplified)
                # Actual implementation would need full protocol parsing
                motion_detected = len(data) > 0  # Simplified detection
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
                    'data_length': len(data),
                    'raw_data': data.hex() if data else None,
                    'last_motion_time': self.last_motion_time.isoformat() if self.last_motion_time else None,
                    'time_since_motion_seconds': time_since_motion,
                    'uart_port': self.uart_port,
                    'sensor_model': 'HLK-LD2420'
                }
            
            return {
                'motion_detected': False,
                'motion_count': self.motion_count,
                'data_length': 0,
                'sensor_model': 'HLK-LD2420'
            }
            
        except Exception as e:
            logger.error(f"LD2420 sensor error: {e}")
            return None

class UltrasonicSensor(BaseSensor):
    """HC-SR04 Ultrasonic Range Finder"""
    def __init__(self, sensor_id: str = "HCSR04-01", asset_id: str = "ULTRASONIC-01",
                 trigger_pin: int = 18, echo_pin: int = 24):
        super().__init__(sensor_id, asset_id, "Zone-7")
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.setup_pins()
    
    def setup_pins(self):
        if not GPIO_AVAILABLE:
            self.is_active = False
            logger.warning("GPIO not available - HC-SR04 sensor not active")
            return
            
        try:
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            GPIO.output(self.trigger_pin, False)
            time.sleep(0.1)  # Let sensor settle
            self.is_active = True
            logger.info("HC-SR04 ultrasonic sensor initialized")
        except Exception as e:
            self.is_active = False
            logger.error(f"Error setting up HC-SR04 sensor: {e}")
    
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
                    logger.debug("HC-SR04 timeout waiting for echo start")
                    return None
            
            # Wait for echo end with timeout
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if time.time() - timeout_start > 0.5:  # 500ms timeout
                    logger.debug("HC-SR04 timeout waiting for echo end")
                    return None
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2
            
            # Validate distance reading (HC-SR04 range: 2cm to 400cm)
            if 2 <= distance <= 400:
                return {
                    'distance_cm': round(distance, 2),
                    'distance_inches': round(distance / 2.54, 2),
                    'distance_meters': round(distance / 100, 3),
                    'pulse_duration_us': round(pulse_duration * 1000000, 2),
                    'object_detected': distance < 100,  # Object within 1 meter
                    'pins': {'trigger': self.trigger_pin, 'echo': self.echo_pin},
                    'sensor_model': 'HC-SR04'
                }
            else:
                logger.debug(f"HC-SR04 invalid distance: {distance}cm")
                return None
            
        except Exception as e:
            logger.error(f"HC-SR04 sensor error: {e}")
            return None
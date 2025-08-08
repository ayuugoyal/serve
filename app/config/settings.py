# Configuration settings for IoT Sensor Monitoring System
# Real Hardware Sensors - NO SIMULATION

# Alert configurations with realistic thresholds for real sensors
ALERT_CONFIGURATIONS = {
    "Smart_HVAC_Load_Control": {
        "enabled": True,
        "temp_threshold": 23.0,  # Celsius - optimal temperature for energy saving
        "humidity_threshold": 60.0,  # Percentage - high humidity threshold
        "air_quality_threshold": 1000,  # PPM - acceptable air quality level
        "cooldown_minutes": 30,
        "priority": "Medium",
        "description": "Optimize HVAC based on temperature, humidity and air quality"
    },
    
    "Predictive_Sick_Building_Alert": {
        "enabled": True,
        "air_quality_ppm_threshold": 1500,  # PPM - poor air quality
        "humidity_threshold": 70.0,  # High humidity + poor air = sick building risk
        "temperature_min": 16.0,  # Too cold
        "temperature_max": 28.0,  # Too hot
        "cooldown_minutes": 15,
        "priority": "High",
        "description": "Detect conditions that may cause sick building syndrome"
    },
    
    "People_Density_Alert": {
        "enabled": True,
        "motion_count_threshold": 15,  # Motion events in time window
        "distance_threshold": 100,  # cm - close proximity detection
        "vibration_threshold": 200,  # Vibration amplitude for high activity
        "time_window_minutes": 10,  # Time window for counting events
        "cooldown_minutes": 10,
        "priority": "High",
        "description": "High occupancy/activity detection based on motion and vibration"
    },
    
    "Zone_Level_Attendance_Accuracy": {
        "enabled": True,
        "motion_timeout_minutes": 20,  # No motion detected for this long
        "radar_timeout_minutes": 15,  # No radar detection for this long
        "cooldown_minutes": 20,
        "priority": "Medium",
        "description": "Detect unoccupied zones that may be marked as occupied"
    },
    
    "Dehumidifier_Smart_Trigger": {
        "enabled": True,
        "humidity_threshold": 75.0,  # High humidity requiring dehumidification
        "duration_minutes": 15,  # Sustained high humidity duration
        "temperature_factor": True,  # Consider temperature in decision
        "cooldown_minutes": 20,
        "priority": "High",
        "description": "Activate dehumidifier when humidity is high for extended period"
    },
    
    "Smart_Ventilation_Escalation": {
        "enabled": True,
        "air_quality_ppm_threshold": 1200,  # Poor air quality
        "dust_density_threshold": 50.0,  # μg/m³ - unhealthy dust levels
        "motion_required": True,  # Only alert if people present
        "cooldown_minutes": 10,
        "priority": "High",
        "description": "Escalate ventilation when air quality degrades with occupancy"
    },
    
    "Real_Time_ESG_Score": {
        "enabled": True,
        "esg_score_threshold": 70,  # Minimum acceptable ESG score
        "temperature_weight": 0.3,  # Weight factors for ESG calculation
        "humidity_weight": 0.2,
        "air_quality_weight": 0.3,
        "dust_weight": 0.2,
        "cooldown_minutes": 30,
        "priority": "Medium",
        "description": "Monitor real-time ESG environmental performance"
    },
    
    "VIP_Room_Air_Quality": {
        "enabled": True,
        "air_quality_ppm_max": 800,  # Stricter air quality for VIP areas
        "dust_density_max": 25.0,  # μg/m³ - stricter dust levels
        "temp_min": 22.0,  # Optimal temperature range
        "temp_max": 26.0,
        "humidity_max": 60.0,  # Maximum acceptable humidity
        "light_level_min": 100,  # Minimum lux for comfort
        "cooldown_minutes": 15,
        "priority": "High",
        "description": "Maintain premium air quality standards in VIP areas"
    },
    
    "Facility_Cleaning_Trigger": {
        "enabled": True,
        "dust_density_threshold": 75.0,  # μg/m³ - cleaning required
        "humidity_threshold": 70.0,  # High humidity indicates cleaning need
        "vibration_activity_threshold": 500,  # High activity = more cleaning needed
        "duration_minutes": 30,  # Sustained poor conditions
        "cooldown_minutes": 45,
        "priority": "Medium",
        "description": "Schedule cleaning based on dust, humidity and activity levels"
    },
    
    "Carbon_Penalty_Avoidance": {
        "enabled": True,
        "air_quality_ppm_threshold": 1000,  # Regulatory compliance threshold
        "exposure_hours_threshold": 2.0,  # Hours of exposure to poor air quality
        "dust_compliance_threshold": 150.0,  # μg/m³ - regulatory limit
        "cooldown_minutes": 60,
        "priority": "High",
        "description": "Avoid carbon penalties through environmental compliance"
    },
    
    "Equipment_Vibration_Alert": {
        "enabled": True,
        "vibration_threshold": 300,  # High vibration amplitude
        "sustained_vibration_minutes": 5,  # Continuous vibration duration
        "cooldown_minutes": 15,
        "priority": "Medium",
        "description": "Detect equipment malfunction through abnormal vibration"
    },
    
    "Security_Motion_Alert": {
        "enabled": True,
        "radar_sensitivity": "high",  # LD2420 sensitivity setting
        "after_hours_only": True,  # Only alert outside business hours
        "distance_threshold": 200,  # cm - detection range
        "cooldown_minutes": 5,
        "priority": "High",
        "description": "Security alert for motion detection during off-hours"
    }
}

# Real sensor hardware configurations
SENSOR_CONFIG = {
    "temperature_humidity": {
        "sensor_type": "DHT22",
        "data_pin": 22,
        "update_interval": 2,  # DHT22 minimum interval
        "warmup_time": 2,  # seconds
        "retry_count": 3,
        "retry_delay": 2,
        "calibration": {
            "temp_offset": 0.0,  # Celsius adjustment
            "humidity_offset": 0.0  # Percentage adjustment
        }
    },
    
    "air_quality": {
        "sensor_type": "MQ135",
        "digital_pin": 25,
        "spi_channel": 0,
        "adc_channel": 0,
        "update_interval": 1,
        "warmup_time": 180,  # 3 minutes warmup required
        "calibration": {
            "rs_air": 76.63,  # Resistance in clean air (calibrate this!)
            "r0": 10.0,  # Load resistance in KΩ
            "voltage_ref": 3.3  # Reference voltage
        }
    },
    
    "light_sensor": {
        "sensor_type": "BH1750",
        "i2c_address": 0x23,
        "i2c_bus": 1,
        "update_interval": 1,
        "measurement_mode": "CONTINUOUS_HIGH_RES",  # or CONTINUOUS_LOW_RES, ONE_TIME
        "calibration": {
            "lux_factor": 1.0  # Calibration multiplier
        }
    },
    
    "dust_sensor": {
        "sensor_type": "GP2Y1010AU0F",
        "led_pin": 7,
        "adc_channel": 1,
        "spi_channel": 0,
        "update_interval": 1,
        "led_pulse_duration": 0.00028,  # 280μs LED pulse
        "calibration": {
            "voltage_ref": 5.0,
            "baseline_voltage": 0.1,
            "sensitivity": 400  # μg/m³ per volt
        }
    },
    
    "vibration_sensor": {
        "sensor_type": "PIEZO",
        "adc_channel": 2,
        "spi_channel": 0,
        "update_interval": 0.1,  # Fast sampling for vibration
        "detection_threshold": 100,
        "sample_count": 10,  # Samples per reading
        "calibration": {
            "sensitivity": 1.0,
            "baseline_filter": True
        }
    },
    
    "motion_radar": {
        "sensor_type": "HLK_LD2420",
        "uart_port": "/dev/ttyUSB0",  # or /dev/ttyAMA0 for GPIO UART
        "baud_rate": 256000,
        "update_interval": 0.5,
        "timeout": 1.0,
        "config": {
            "detection_range": 600,  # cm
            "sensitivity": 50,  # 0-100
            "motion_trigger": 50,  # Motion sensitivity
            "static_trigger": 50   # Static detection sensitivity
        }
    },
    
    "ultrasonic": {
        "sensor_type": "HC_SR04",
        "trigger_pin": 18,
        "echo_pin": 24,
        "update_interval": 0.1,
        "speed_of_sound": 34300,  # cm/s at 20°C
        "timeout": 0.5,  # seconds
        "calibration": {
            "distance_offset": 0.0,  # cm adjustment
            "temperature_compensation": True
        }
    }
}

# MCP3008 ADC Configuration (for analog sensors)
ADC_CONFIG = {
    "enabled": True,
    "spi_bus": 0,
    "spi_device": 0,
    "max_speed_hz": 1000000,
    "voltage_reference": 3.3,
    "resolution_bits": 10,  # 10-bit ADC (0-1023)
    "channels": {
        0: "air_quality_analog",    # MQ135 analog output
        1: "dust_sensor_analog",    # GP2Y1010AU0F analog output
        2: "vibration_analog",      # Piezo vibration sensor
        3: "spare_analog_1",
        4: "spare_analog_2",
        5: "spare_analog_3",
        6: "spare_analog_4",
        7: "spare_analog_5"
    }
}

# I2C Configuration
I2C_CONFIG = {
    "enabled": True,
    "bus_number": 1,  # I2C bus 1 on Raspberry Pi
    "devices": {
        0x23: "BH1750_light_sensor",
        # Add other I2C sensors here as needed
        # 0x48: "ADS1015_ADC",
        # 0x76: "BME280_environmental"
    }
}

# UART/Serial Configuration  
UART_CONFIG = {
    "enabled": True,
    "ports": {
        "/dev/ttyUSB0": {
            "device": "HLK_LD2420",
            "baud_rate": 256000,
            "timeout": 1.0,
            "parity": "N",
            "stopbits": 1,
            "bytesize": 8
        },
        "/dev/ttyAMA0": {
            "device": "GPIO_UART",
            "baud_rate": 115200,
            "timeout": 1.0,
            "enabled": False  # Disable if using USB-Serial
        }
    }
}

# System Configuration
SYSTEM_CONFIG = {
    "hardware_mode": "REAL_SENSORS_ONLY",
    "simulation_enabled": False,  # NEVER enable simulation
    "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "sensor_read_interval": 1.0,  # seconds between sensor updates
    "alert_check_interval": 1.0,  # seconds between alert checks
    "websocket_update_interval": 2.0,  # seconds between WebSocket updates
    "max_alerts_stored": 1000,
    "max_sensor_failures": 5,  # Mark sensor inactive after this many failures
    "sensor_timeout": 60,  # seconds - sensor considered dead if no reading
    "gpio_cleanup_on_exit": True,
    "enable_diagnostics": True,
    "enable_hardware_monitoring": True
}

# Database Configuration (if using database storage)
DATABASE_CONFIG = {
    "enabled": False,  # Set to True to enable database logging
    "type": "sqlite",  # sqlite, postgresql, mysql
    "connection_string": "sqlite:///sensor_data.db",
    "tables": {
        "sensor_readings": "sensor_readings",
        "alerts": "alerts",
        "system_logs": "system_logs"
    },
    "retention_days": 30  # Auto-delete old records
}

# Web Server Configuration
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": False,  # Set to False in production
    "log_level": "info",
    "cors_origins": ["*"],  # Restrict in production
    "websocket_max_connections": 10,
    "api_rate_limit": 100,  # requests per minute
    "enable_docs": True,  # Set to False in production for security
    "ssl_enabled": False,
    "ssl_certfile": None,
    "ssl_keyfile": None
}

# Calibration and Environmental Constants
ENVIRONMENTAL_CONSTANTS = {
    "standard_temperature": 20.0,  # Celsius
    "standard_pressure": 1013.25,  # hPa
    "standard_humidity": 50.0,  # Percentage
    "speed_of_sound_base": 34300,  # cm/s at 20°C
    "temperature_sound_coefficient": 60,  # cm/s per °C
    "air_density_stp": 1.225,  # kg/m³ at STP
    "gas_constants": {
        "R": 8.314,  # Universal gas constant
        "molecular_weight_air": 28.97  # g/mol
    }
}

# Quality Thresholds for Categorization
QUALITY_THRESHOLDS = {
    "air_quality_ppm": {
        "excellent": 400,
        "good": 1000,
        "moderate": 2000,
        "poor": 5000,
        "hazardous": float('inf')
    },
    "dust_density_ugm3": {
        "excellent": 12,
        "good": 35,
        "moderate": 55,
        "unhealthy_sensitive": 150,
        "unhealthy": 250,
        "hazardous": float('inf')
    },
    "light_level_lux": {
        "very_dark": 1,
        "dark": 10,
        "dim": 50,
        "normal_indoor": 200,
        "bright_indoor": 500,
        "very_bright": 1000,
        "direct_sunlight": float('inf')
    },
    "vibration_amplitude": {
        "none": 50,
        "light": 150,
        "moderate": 300,
        "strong": 500,
        "very_strong": float('inf')
    }
}

# Comfort Zone Definitions
COMFORT_ZONES = {
    "temperature": {
        "min_comfortable": 20.0,
        "max_comfortable": 26.0,
        "min_acceptable": 18.0,
        "max_acceptable": 28.0
    },
    "humidity": {
        "min_comfortable": 40.0,
        "max_comfortable": 60.0,
        "min_acceptable": 30.0,
        "max_acceptable": 70.0
    },
    "air_quality": {
        "excellent_max": 400,
        "good_max": 1000,
        "acceptable_max": 2000
    },
    "light_level": {
        "min_indoor": 100,
        "optimal_office": 500,
        "max_comfortable": 1000
    }
}

# Hardware-specific pin assignments (easily modifiable)
PIN_ASSIGNMENTS = {
    "GPIO": {
        "DHT22_data": 22,
        "MQ135_digital": 25,
        "GP2Y1010AU0F_led": 7,
        "HC_SR04_trigger": 18,
        "HC_SR04_echo": 24,
        # Reserve some pins for future expansion
        "spare_digital_1": 12,
        "spare_digital_2": 16,
        "spare_digital_3": 20,
        "spare_digital_4": 21
    },
    "SPI": {
        "MOSI": 10,  # GPIO 10
        "MISO": 9,   # GPIO 9
        "SCLK": 11,  # GPIO 11
        "CE0": 8,    # GPIO 8 (Chip Enable 0)
        "CE1": 7     # GPIO 7 (Chip Enable 1)
    },
    "I2C": {
        "SDA": 2,    # GPIO 2
        "SCL": 3     # GPIO 3
    },
    "UART": {
        "TX": 14,    # GPIO 14
        "RX": 15     # GPIO 15
    }
}

# Development and Debug Settings
DEBUG_CONFIG = {
    "verbose_logging": False,
    "sensor_simulation": False,  # NEVER enable in production
    "mock_hardware": False,     # For testing without hardware
    "debug_intervals": {
        "sensor_status_log": 300,  # Log sensor status every 5 minutes
        "memory_usage_log": 600,   # Log memory usage every 10 minutes
        "performance_log": 900     # Log performance metrics every 15 minutes
    },
    "test_mode": False,
    "development_server": False
}

# Export configuration validation
def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Check that simulation is disabled
    if SYSTEM_CONFIG.get("simulation_enabled", False):
        errors.append("❌ Simulation must be disabled for real hardware operation")
    
    if DEBUG_CONFIG.get("sensor_simulation", False):
        errors.append("❌ Sensor simulation must be disabled")
    
    # Validate pin assignments don't conflict
    used_pins = []
    for category, pins in PIN_ASSIGNMENTS.items():
        if category == "GPIO":
            for pin_name, pin_num in pins.items():
                if pin_num in used_pins:
                    errors.append(f"❌ GPIO pin {pin_num} assigned to multiple functions")
                used_pins.append(pin_num)
    
    # Check sensor intervals are reasonable
    for sensor, config in SENSOR_CONFIG.items():
        interval = config.get("update_interval", 1)
        if interval < 0.1:
            errors.append(f"⚠️ {sensor} update interval ({interval}s) may be too fast")
    
    return errors

# Auto-validate on import
_validation_errors = validate_config()
if _validation_errors:
    import logging
    logger = logging.getLogger(__name__)
    for error in _validation_errors:
        logger.error(f"Configuration Error: {error}")
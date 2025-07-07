# Alert configurations
ALERT_CONFIGURATIONS = {
    "Smart_HVAC_Load_Control": {
        "enabled": True,
        "temp_threshold": 23.0,
        "humidity_threshold": 60.0,
        "co2_threshold": 700,
        "cooldown_minutes": 30,
        "priority": "Medium"
    },
    "Predictive_Sick_Building_Alert": {
        "enabled": True,
        "aqi_threshold": 150,
        "co2_threshold": 1200,
        "cooldown_minutes": 15,
        "priority": "High"
    },
    "People_Density_Alert": {
        "enabled": True,
        "entry_count_threshold": 19,
        "co2_threshold": 640,
        "cooldown_minutes": 10,
        "priority": "High"
    },
    "Zone_Level_Attendance_Accuracy": {
        "enabled": True,
        "motion_timeout_minutes": 20,
        "cooldown_minutes": 20,
        "priority": "Medium"
    },
    "Dehumidifier_Smart_Trigger": {
        "enabled": True,
        "humidity_threshold": 75.0,
        "duration_minutes": 15,
        "cooldown_minutes": 20,
        "priority": "High"
    },
    "Smart_Ventilation_Escalation": {
        "enabled": True,
        "co2_threshold": 1000,
        "aqi_threshold": 150,
        "people_threshold": 5,
        "cooldown_minutes": 10,
        "priority": "High"
    },
    "Real_Time_ESG_Score": {
        "enabled": True,
        "esg_score_threshold": 70,
        "cooldown_minutes": 30,
        "priority": "Medium"
    },
    "VIP_Room_Air_Quality": {
        "enabled": True,
        "co2_threshold": 1000,
        "aqi_threshold": 150,
        "temp_min": 22,
        "temp_max": 26,
        "cooldown_minutes": 15,
        "priority": "High"
    },
    "Toilet_Occupancy_Cleaning": {
        "enabled": True,
        "humidity_threshold": 70.0,
        "duration_minutes": 30,
        "usage_threshold": 50,
        "cooldown_minutes": 45,
        "priority": "Medium"
    },
    "Carbon_Penalty_Avoidance": {
        "enabled": True,
        "co2_threshold": 1000,
        "exposure_hours_threshold": 5.0,
        "cooldown_minutes": 60,
        "priority": "High"
    }
}

# Sensor configurations
SENSOR_CONFIG = {
    "ultrasonic": {
        "trigger_pin": 18,
        "echo_pin": 24,
        "update_interval": 1
    },
    "air_quality": {
        "digital_pin": 25,
        "analog_pin": 26,
        "update_interval": 2
    },
    "temperature_humidity": {
        "data_pin": 22,
        "update_interval": 2
    },
    "light_sensor": {
        "ldr_pin": 21,
        "update_interval": 1
    },
    "motion_sensor": {
        "data_pin": 17,
        "update_interval": 0.5
    }
}

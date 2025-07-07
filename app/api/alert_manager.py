import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from collections import defaultdict, deque
from config.settings import ALERT_CONFIGURATIONS

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self):
        self.alerts = deque(maxlen=1000)  # Store last 1000 alerts
        self.alert_cooldowns = {}
        self.alert_configs = ALERT_CONFIGURATIONS.copy()
        
        # Tracking variables for complex alerts
        self.zone_entry_times = defaultdict(list)
        self.daily_usage_stats = defaultdict(int)
        self.co2_exposure_tracking = defaultdict(float)
        self.high_humidity_start_times = {}
        
    def generate_alert(self, alert_type: str, description: str, priority: str = "Medium", zone_id: str = "Zone-1") -> Dict:
        """Generate a new alert"""
        alert_id = f"ALERT_{alert_type}_{int(time.time())}"
        
        alert = {
            "AlertType": alert_type,
            "assetId": "MCN-02",
            "Description": description,
            "Date": datetime.now(timezone.utc).isoformat(),
            "Report": "Smart Building Alert",
            "App": "IoT Sensor System",
            "anchor": zone_id,
            "Stage_x007b__x0023__x007d_": "Active",
            "Failure_x0020_Class": "Smart_Building_Logic",
            "id": alert_id,
            "Priority": priority,
            "OperatorNumber": "SYS-001",
            "OperatorName": "Smart Building AI",
            "ManagerName": "Facility Manager",
            "ManagerNumber": "FM-001",
            "GoogleDriveURL": "NaN"
        }
        
        self.alerts.append(alert)
        logger.info(f"Generated alert: {alert_type} - {description}")
        return alert
    
    def should_generate_alert(self, alert_type: str, cooldown_minutes: int = 5) -> bool:
        """Check if alert should be generated based on cooldown"""
        current_time = datetime.now(timezone.utc)
        
        if alert_type in self.alert_cooldowns:
            time_since_last = (current_time - self.alert_cooldowns[alert_type]).total_seconds()
            if time_since_last < (cooldown_minutes * 60):
                return False
        
        self.alert_cooldowns[alert_type] = current_time
        return True
    
    def check_all_alerts(self, sensor_readings: List[Dict]):
        """Check all alert conditions"""
        # Convert readings to dict for easier access
        readings_dict = {}
        for reading in sensor_readings:
            readings_dict[reading['sensor_type']] = reading
        
        # Check each alert type
        self.check_hvac_load_control(readings_dict)
        self.check_sick_building_alert(readings_dict)
        self.check_people_density_alert(readings_dict)
        self.check_attendance_accuracy(readings_dict)
        self.check_dehumidifier_trigger(readings_dict)
        self.check_ventilation_escalation(readings_dict)
        self.check_esg_score(readings_dict)
        self.check_vip_air_quality(readings_dict)
        self.check_toilet_cleaning_trigger(readings_dict)
        self.check_carbon_penalty_avoidance(readings_dict)
    
    def check_hvac_load_control(self, readings: Dict):
        """Smart HVAC Load Control Alert"""
        config = self.alert_configs.get("Smart_HVAC_Load_Control", {})
        if not config.get("enabled", True):
            return
        
        temp_reading = readings.get('temperature_humidity', {})
        air_reading = readings.get('air_quality', {})
        
        if temp_reading and air_reading:
            temp = temp_reading.get('temperature_celsius', 0)
            humidity = temp_reading.get('humidity_percent', 0)
            co2_ppm = air_reading.get('co2_equivalent', 0)
            
            temp_threshold = config.get('temp_threshold', 23.0)
            humidity_threshold = config.get('humidity_threshold', 60.0)
            co2_threshold = config.get('co2_threshold', 700)
            cooldown = config.get('cooldown_minutes', 30)
            priority = config.get('priority', 'Medium')
            
            if temp < temp_threshold and humidity > humidity_threshold and co2_ppm < co2_threshold:
                if self.should_generate_alert("Smart_HVAC_Load_Control", cooldown):
                    description = (f"🌡️ Optimal conditions for reduced HVAC load: "
                                 f"Temp = {temp}°C, Humidity = {humidity}%, CO₂ = {co2_ppm} ppm. "
                                 f"Switch to energy-saving mode.")
                    self.generate_alert("Smart_HVAC_Load_Control", description, priority)
    
    def check_sick_building_alert(self, readings: Dict):
        """Predictive Sick Building Alert"""
        config = self.alert_configs.get("Predictive_Sick_Building_Alert", {})
        if not config.get("enabled", True):
            return
        
        air_reading = readings.get('air_quality', {})
        motion_reading = readings.get('motion_sensor', {})
        temp_reading = readings.get('temperature_humidity', {})
        
        if air_reading and motion_reading:
            aqi = air_reading.get('air_quality_ppm', 0)
            co2_ppm = air_reading.get('co2_equivalent', 0)
            motion_detected = motion_reading.get('motion_detected', False)
            humidity = temp_reading.get('humidity_percent', 0) if temp_reading else 0
            
            aqi_threshold = config.get('aqi_threshold', 150)
            co2_threshold = config.get('co2_threshold', 1200)
            cooldown = config.get('cooldown_minutes', 15)
            priority = config.get('priority', 'High')
            
            if (aqi > aqi_threshold or co2_ppm > co2_threshold) and motion_detected:
                if self.should_generate_alert("Predictive_Sick_Building_Alert", cooldown):
                    description = (f"⚠️ Poor air quality detected with occupancy: "
                                 f"AQI = {aqi}, CO₂ = {co2_ppm} ppm, Humidity = {humidity}%. "
                                 f"Activate ventilation immediately.")
                    self.generate_alert("Predictive_Sick_Building_Alert", description, priority)
    
    def check_people_density_alert(self, readings: Dict):
        """People Density Alert"""
        config = self.alert_configs.get("People_Density_Alert", {})
        if not config.get("enabled", True):
            return
        
        ultrasonic_reading = readings.get('ultrasonic', {})
        air_reading = readings.get('air_quality', {})
        
        if ultrasonic_reading and air_reading:
            distance = ultrasonic_reading.get('distance_cm', 200)
            co2_ppm = air_reading.get('co2_equivalent', 0)
            
            # Simulate entry tracking
            if distance < 100:  # Someone detected
                current_time = datetime.now(timezone.utc)
                zone_id = ultrasonic_reading.get('zone_id', 'Zone-1')
                self.zone_entry_times[zone_id].append(current_time)
                
                # Keep only entries from last 10 minutes
                cutoff_time = current_time - timedelta(minutes=10)
                self.zone_entry_times[zone_id] = [t for t in self.zone_entry_times[zone_id] if t > cutoff_time]
                
                recent_entries = len(self.zone_entry_times[zone_id])
                entry_threshold = config.get('entry_count_threshold', 19)
                co2_threshold = config.get('co2_threshold', 640)
                cooldown = config.get('cooldown_minutes', 10)
                priority = config.get('priority', 'High')
                
                if recent_entries > entry_threshold and co2_ppm < co2_threshold:
                    if self.should_generate_alert("People_Density_Alert", cooldown):
                        description = (f"🚨 Overcrowding detected: {recent_entries} entries in 10 mins. "
                                     f"CO₂ = {co2_ppm} ppm. Increase ventilation immediately.")
                        self.generate_alert("People_Density_Alert", description, priority, zone_id)
    
    # Add more alert check methods here...
    
    def get_all_alerts(self) -> List[Dict]:
        """Get all alerts"""
        return list(self.alerts)
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts"""
        recent_alerts = list(self.alerts)[-limit:]
        return sorted(recent_alerts, key=lambda x: x['Date'], reverse=True)
    
    def get_alert_configs(self) -> List[Dict]:
        """Get alert configurations"""
        config_list = []
        for alert_type, config in self.alert_configs.items():
            config_item = {
                "alert_type": alert_type,
                "enabled": config.get("enabled", True),
                "cooldown_minutes": config.get("cooldown_minutes", 5),
                "priority": config.get("priority", "Medium"),
                "parameters": {k: v for k, v in config.items() 
                             if k not in ["enabled", "cooldown_minutes", "priority"]}
            }
            config_list.append(config_item)
        return config_list
    
    def update_alert_config(self, alert_type: str, config_updates: Dict) -> Dict:
        """Update alert configuration"""
        if alert_type not in self.alert_configs:
            raise ValueError(f"Alert type '{alert_type}' not found")
        
        self.alert_configs[alert_type].update(config_updates)
        
        return {
            "status": "success",
            "message": f"Alert configuration updated for {alert_type}",
            "updated_config": self.alert_configs[alert_type],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_alerts_summary(self) -> Dict:
        """Get alerts summary"""
        alert_summary = {}
        total_alerts = len(self.alerts)
        
        for alert in self.alerts:
            alert_type = alert.get('AlertType', 'Unknown')
            if alert_type not in alert_summary:
                alert_summary[alert_type] = {
                    'count': 0,
                    'last_triggered': None,
                    'priority': alert.get('Priority', 'Medium'),
                    'enabled': self.alert_configs.get(alert_type, {}).get('enabled', True)
                }
            
            alert_summary[alert_type]['count'] += 1
            alert_date = alert.get('Date')
            if not alert_summary[alert_type]['last_triggered'] or alert_date > alert_summary[alert_type]['last_triggered']:
                alert_summary[alert_type]['last_triggered'] = alert_date
        
        return {
            'total_alerts': total_alerts,
            'alert_types': alert_summary,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

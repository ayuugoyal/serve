import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from collections import defaultdict, deque
from config.settings import ALERT_CONFIGURATIONS

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self, db_manager=None):
        self.alerts = deque(maxlen=1000)  # Store last 1000 alerts
        self.alert_cooldowns = {}
        self.alert_configs = ALERT_CONFIGURATIONS.copy()
        self.db_manager = db_manager
        
        # Tracking variables for complex alerts
        self.zone_entry_times = defaultdict(list)
        self.daily_usage_stats = defaultdict(int)
        self.co2_exposure_tracking = defaultdict(float)
        self.high_humidity_start_times = {}
        
    def set_db_manager(self, db_manager):
        """Set the database manager for asset ID resolution"""
        self.db_manager = db_manager
        logger.info("Database manager connected to AlertManager")
        
    async def generate_alert(self, alert_type: str, description: str, priority: str = "Medium", zone_id: str = "Zone-1") -> Dict:
        """Generate a new alert with automatic asset ID assignment"""
        alert_id = f"ALERT_{alert_type}_{int(time.time())}"
        
        # Try to get asset ID from database
        asset_id = "no-asset-id-assigned"  # Default
        if self.db_manager:
            try:
                asset_id = await self.db_manager.get_alert_asset_id(alert_type)
                logger.debug(f"Resolved asset ID '{asset_id}' for alert type '{alert_type}'")
            except Exception as e:
                logger.warning(f"Failed to resolve asset ID for alert {alert_type}: {e}")
                asset_id = "no-asset-id-assigned"
        
        alert = {
            "AlertType": alert_type,
            "assetId": asset_id,
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
        logger.info(f"Generated alert: {alert_type} - {description} (Asset ID: {asset_id})")
        return alert

    def generate_alert_sync(self, alert_type: str, description: str, priority: str = "Medium", zone_id: str = "Zone-1") -> Dict:
        """Synchronous version of generate_alert for backward compatibility"""
        alert_id = f"ALERT_{alert_type}_{int(time.time())}"
        
        alert = {
            "AlertType": alert_type,
            "assetId": "no-asset-id-assigned",  # Will be updated later by API layer
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
            if reading.get('status') == 'active':  # Only process active sensors
                readings_dict[reading['sensor_type']] = reading
        
        # Only check alerts if we have active sensors
        if not readings_dict:
            return
        
        # Check each alert type (using sync version for now)
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
            
            if 'gas_detected' in air_reading:
                gas_level = "Low" if not air_reading.get('gas_detected', False) else "High"
            else:
                gas_level = "Unknown"
            
            temp_threshold = config.get('temp_threshold', 23.0)
            humidity_threshold = config.get('humidity_threshold', 60.0)
            cooldown = config.get('cooldown_minutes', 30)
            priority = config.get('priority', 'Medium')
            
            if temp and humidity and temp < temp_threshold and humidity > humidity_threshold:
                if self.should_generate_alert("Smart_HVAC_Load_Control", cooldown):
                    description = (f"🌡️ Optimal conditions for reduced HVAC load: "
                                 f"Temp = {temp}°C, Humidity = {humidity}%, Gas Level = {gas_level}. "
                                 f"Consider switching to energy-saving mode.")
                    self.generate_alert_sync("Smart_HVAC_Load_Control", description, priority)
    
    def check_sick_building_alert(self, readings: Dict):
        """Predictive Sick Building Alert"""
        config = self.alert_configs.get("Predictive_Sick_Building_Alert", {})
        if not config.get("enabled", True):
            return
        
        air_reading = readings.get('air_quality', {})
        motion_reading = readings.get('motion_sensor', {})
        temp_reading = readings.get('temperature_humidity', {})
        
        if air_reading and motion_reading and temp_reading:
            gas_detected = air_reading.get('gas_detected', False)
            motion_detected = motion_reading.get('motion_detected', False)
            humidity = temp_reading.get('humidity_percent', 0)
            temperature = temp_reading.get('temperature_celsius', 0)
            
            cooldown = config.get('cooldown_minutes', 15)
            priority = config.get('priority', 'High')
            
            # Alert if gas detected with people present and high humidity
            if gas_detected and motion_detected and humidity > 70:
                if self.should_generate_alert("Predictive_Sick_Building_Alert", cooldown):
                    description = (f"⚠️ Poor air quality detected with occupancy: "
                                 f"Gas Detected = {gas_detected}, Motion = {motion_detected}, "
                                 f"Humidity = {humidity}%, Temp = {temperature}°C. "
                                 f"Activate ventilation immediately.")
                    self.generate_alert_sync("Predictive_Sick_Building_Alert", description, priority)
    
    def check_people_density_alert(self, readings: Dict):
        """People Density Alert based on motion and distance"""
        config = self.alert_configs.get("People_Density_Alert", {})
        if not config.get("enabled", True):
            return
        
        ultrasonic_reading = readings.get('ultrasonic', {})
        motion_reading = readings.get('motion_sensor', {})
        
        if ultrasonic_reading and motion_reading:
            distance = ultrasonic_reading.get('distance_cm', 200)
            motion_count = motion_reading.get('motion_count', 0)
            motion_detected = motion_reading.get('motion_detected', False)
            
            # Track motion events
            if motion_detected and distance < 100:  # Close proximity with motion
                current_time = datetime.now(timezone.utc)
                zone_id = ultrasonic_reading.get('zone_id', 'Zone-1')
                self.zone_entry_times[zone_id].append(current_time)
                
                # Keep only entries from last 10 minutes
                cutoff_time = current_time - timedelta(minutes=10)
                self.zone_entry_times[zone_id] = [t for t in self.zone_entry_times[zone_id] if t > cutoff_time]
                
                recent_entries = len(self.zone_entry_times[zone_id])
                entry_threshold = config.get('entry_count_threshold', 10)
                cooldown = config.get('cooldown_minutes', 10)
                priority = config.get('priority', 'High')
                
                if recent_entries > entry_threshold:
                    if self.should_generate_alert("People_Density_Alert", cooldown):
                        description = (f"🚨 High activity detected: {recent_entries} motion events in 10 mins. "
                                     f"Distance = {distance}cm, Motion Count = {motion_count}. "
                                     f"Consider increasing ventilation.")
                        self.generate_alert_sync("People_Density_Alert", description, priority, zone_id)
    
    def check_attendance_accuracy(self, readings: Dict):
        """Zone-Level Attendance Accuracy based on motion patterns"""
        config = self.alert_configs.get("Zone_Level_Attendance_Accuracy", {})
        if not config.get("enabled", True):
            return
        
        motion_reading = readings.get('motion_sensor', {})
        
        if motion_reading:
            time_since_motion = motion_reading.get('time_since_motion_seconds')
            
            motion_timeout_minutes = config.get('motion_timeout_minutes', 20)
            cooldown = config.get('cooldown_minutes', 20)  
            priority = config.get('priority', 'Medium')
            
            if time_since_motion and time_since_motion > motion_timeout_minutes * 60:
                if self.should_generate_alert("Zone_Level_Attendance_Accuracy", cooldown):
                    description = (f"📛 No motion detected for {time_since_motion//60} minutes. "
                                 f"Zone may be unoccupied but marked as occupied. Please verify.")
                    self.generate_alert_sync("Zone_Level_Attendance_Accuracy", description, priority)

    def check_dehumidifier_trigger(self, readings: Dict):
        """Dehumidifier Smart Trigger"""
        config = self.alert_configs.get("Dehumidifier_Smart_Trigger", {})
        if not config.get("enabled", True):
            return
        
        temp_reading = readings.get('temperature_humidity', {})
        
        if temp_reading:
            humidity = temp_reading.get('humidity_percent', 0)
            temperature = temp_reading.get('temperature_celsius', 0)
            
            # Track high humidity duration per zone
            zone_id = temp_reading.get('zone_id', 'Zone-1')
            
            humidity_threshold = config.get('humidity_threshold', 75.0)
            duration_minutes = config.get('duration_minutes', 15)
            cooldown = config.get('cooldown_minutes', 20)
            priority = config.get('priority', 'High')
            
            if humidity > humidity_threshold:
                if zone_id not in self.high_humidity_start_times:
                    self.high_humidity_start_times[zone_id] = datetime.now(timezone.utc)
                else:
                    duration = (datetime.now(timezone.utc) - self.high_humidity_start_times[zone_id]).total_seconds()
                    if duration > duration_minutes * 60:
                        if self.should_generate_alert("Dehumidifier_Smart_Trigger", cooldown):
                            description = (f"💧 {zone_id}: Humidity = {humidity}% for {duration//60:.0f} minutes. "
                                         f"Temperature = {temperature}°C. "
                                         f"Risk of condensation and mold - activate dehumidifier.")
                            self.generate_alert_sync("Dehumidifier_Smart_Trigger", description, priority, zone_id)
            else:
                # Reset timer when humidity drops
                if zone_id in self.high_humidity_start_times:
                    del self.high_humidity_start_times[zone_id]

    def check_ventilation_escalation(self, readings: Dict):
        """Smart Ventilation Escalation"""
        config = self.alert_configs.get("Smart_Ventilation_Escalation", {})
        if not config.get("enabled", True):
            return
        
        air_reading = readings.get('air_quality', {})
        ultrasonic_reading = readings.get('ultrasonic', {})
        motion_reading = readings.get('motion_sensor', {})
        
        if air_reading and motion_reading:
            gas_detected = air_reading.get('gas_detected', False)
            motion_detected = motion_reading.get('motion_detected', False)
            motion_count = motion_reading.get('motion_count', 0)
            
            # Estimate occupancy from motion patterns
            recent_motion = motion_count > 0 and motion_detected
            
            cooldown = config.get('cooldown_minutes', 10)
            priority = config.get('priority', 'High')
            
            if gas_detected and recent_motion:
                distance = ultrasonic_reading.get('distance_cm', 200) if ultrasonic_reading else 200
                if self.should_generate_alert("Smart_Ventilation_Escalation", cooldown):
                    description = (f"🌫️ Air quality degraded with occupancy: "
                                 f"Gas Detected = {gas_detected}, Motion = {motion_detected}, "
                                 f"Distance = {distance}cm. Initiate ventilation escalation.")
                    self.generate_alert_sync("Smart_Ventilation_Escalation", description, priority)

    def check_esg_score(self, readings: Dict):
        """Real-Time ESG Score by Zone"""
        config = self.alert_configs.get("Real_Time_ESG_Score", {})
        if not config.get("enabled", True):
            return
        
        temp_reading = readings.get('temperature_humidity', {})
        air_reading = readings.get('air_quality', {})
        
        if temp_reading and air_reading:
            temp = temp_reading.get('temperature_celsius', 0)
            humidity = temp_reading.get('humidity_percent', 0)
            gas_detected = air_reading.get('gas_detected', False)
            
            # Calculate ESG score based on environmental conditions
            temp_score = 100 if 20 <= temp <= 26 else 70 if 18 <= temp <= 28 else 40
            humidity_score = 100 if 40 <= humidity <= 60 else 70 if 30 <= humidity <= 70 else 40
            air_score = 100 if not gas_detected else 40
            
            esg_score = (temp_score + humidity_score + air_score) / 3
            
            esg_score_threshold = config.get('esg_score_threshold', 70)
            cooldown = config.get('cooldown_minutes', 30)
            priority = config.get('priority', 'Medium')
            
            if esg_score < esg_score_threshold:
                if self.should_generate_alert("Real_Time_ESG_Score", cooldown):
                    zone_id = temp_reading.get('zone_id', 'Zone-1')
                    description = (f"📈 {zone_id} ESG Score: {esg_score:.0f}% (Below Target). "
                                 f"Temp = {temp}°C, Humidity = {humidity}%, "
                                 f"Air Quality = {'Poor' if gas_detected else 'Good'}. "
                                 f"Review environmental controls.")
                    self.generate_alert_sync("Real_Time_ESG_Score", description, priority, zone_id)

    def check_vip_air_quality(self, readings: Dict):
        """VIP Room Air Quality Insurance"""
        config = self.alert_configs.get("VIP_Room_Air_Quality", {})
        if not config.get("enabled", True):
            return
        
        temp_reading = readings.get('temperature_humidity', {})
        air_reading = readings.get('air_quality', {})
        
        if temp_reading and air_reading:
            temp = temp_reading.get('temperature_celsius', 0)
            humidity = temp_reading.get('humidity_percent', 0)
            gas_detected = air_reading.get('gas_detected', False)
            
            temp_min = config.get('temp_min', 22)
            temp_max = config.get('temp_max', 26)
            humidity_max = config.get('humidity_max', 60)
            cooldown = config.get('cooldown_minutes', 15)
            priority = config.get('priority', 'High')
            
            # Alert if temperature is good but air quality or humidity is poor
            if temp_min <= temp <= temp_max and (gas_detected or humidity > humidity_max):
                if self.should_generate_alert("VIP_Room_Air_Quality", cooldown):
                    zone_id = temp_reading.get('zone_id', 'Zone-1')
                    issues = []
                    if gas_detected:
                        issues.append("poor air quality")
                    if humidity > humidity_max:
                        issues.append(f"high humidity ({humidity}%)")
                    
                    description = (f"🛑 {zone_id}: Temperature optimal ({temp}°C) but "
                                 f"{' and '.join(issues)}. Immediate attention required.")
                    self.generate_alert_sync("VIP_Room_Air_Quality", description, priority, zone_id)

    def check_toilet_cleaning_trigger(self, readings: Dict):
        """Toilet Occupancy + Cleaning Trigger"""
        config = self.alert_configs.get("Toilet_Occupancy_Cleaning", {})
        if not config.get("enabled", True):
            return
        
        ultrasonic_reading = readings.get('ultrasonic', {})
        temp_reading = readings.get('temperature_humidity', {})
        motion_reading = readings.get('motion_sensor', {})
        
        if ultrasonic_reading and temp_reading and motion_reading:
            distance = ultrasonic_reading.get('distance_cm', 200)
            humidity = temp_reading.get('humidity_percent', 0)
            motion_count = motion_reading.get('motion_count', 0)
            
            zone_id = ultrasonic_reading.get('zone_id', 'Zone-1')
            
            # Track daily usage based on close proximity detections
            if distance < 100:  # Someone very close
                self.daily_usage_stats[zone_id] += 1
            
            humidity_threshold = config.get('humidity_threshold', 70.0)
            duration_minutes = config.get('duration_minutes', 30)
            usage_threshold = config.get('usage_threshold', 25)
            cooldown = config.get('cooldown_minutes', 45)
            priority = config.get('priority', 'Medium')
            
            # Track high humidity duration
            if humidity > humidity_threshold:
                if zone_id not in self.high_humidity_start_times:
                    self.high_humidity_start_times[zone_id] = datetime.now(timezone.utc)
                else:
                    duration = (datetime.now(timezone.utc) - self.high_humidity_start_times[zone_id]).total_seconds()
                    if (duration > duration_minutes * 60 or 
                        self.daily_usage_stats[zone_id] > usage_threshold):
                        if self.should_generate_alert("Toilet_Occupancy_Cleaning", cooldown):
                            description = (f"🚻 {zone_id}: {self.daily_usage_stats[zone_id]} usage events today. "
                                         f"Humidity = {humidity}% for {duration//60:.0f} minutes. "
                                         f"Motion events = {motion_count}. Schedule cleaning.")
                            self.generate_alert_sync("Toilet_Occupancy_Cleaning", description, priority, zone_id)
            else:
                # Reset humidity timer
                if zone_id in self.high_humidity_start_times:
                    del self.high_humidity_start_times[zone_id]

    def check_carbon_penalty_avoidance(self, readings: Dict):
        """Carbon Penalty Avoidance based on air quality"""
        config = self.alert_configs.get("Carbon_Penalty_Avoidance", {})
        if not config.get("enabled", True):
            return
        
        air_reading = readings.get('air_quality', {})
        
        if air_reading:
            gas_detected = air_reading.get('gas_detected', False)
            zone_id = air_reading.get('zone_id', 'Zone-1')
            
            exposure_hours_threshold = config.get('exposure_hours_threshold', 2.0)
            cooldown = config.get('cooldown_minutes', 60)
            priority = config.get('priority', 'High')
            
            # Track gas exposure time (simplified - increment when gas detected)
            if gas_detected:
                self.co2_exposure_tracking[zone_id] += 1/3600  # Add 1 second worth of hours
            
            # Check if exposure exceeds threshold
            if self.co2_exposure_tracking[zone_id] > exposure_hours_threshold:
                if self.should_generate_alert("Carbon_Penalty_Avoidance", cooldown):
                    description = (f"📉 {zone_id}: Poor air quality detected for "
                                 f"{self.co2_exposure_tracking[zone_id]:.1f} hours today. "
                                 f"Gas Detection = {gas_detected}. "
                                 f"ESG compliance risk - improve ventilation.")
                    self.generate_alert_sync("Carbon_Penalty_Avoidance", description, priority, zone_id)
    
    async def update_alert_asset_ids(self):
        """Update asset IDs for all existing alerts"""
        if not self.db_manager:
            return
        
        updated_count = 0
        for alert in self.alerts:
            if alert.get('AlertType') and alert.get('assetId') == 'no-asset-id-assigned':
                try:
                    asset_id = await self.db_manager.get_alert_asset_id(alert['AlertType'])
                    if asset_id != 'no-asset-id-assigned':
                        alert['assetId'] = asset_id
                        updated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to update asset ID for alert {alert['AlertType']}: {e}")
        
        if updated_count > 0:
            logger.info(f"Updated asset IDs for {updated_count} existing alerts")
        
        return updated_count
    
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
                    'enabled': self.alert_configs.get(alert_type, {}).get('enabled', True),
                    'asset_id': alert.get('assetId', 'no-asset-id-assigned')
                }
            
            alert_summary[alert_type]['count'] += 1
            alert_date = alert.get('Date')
            if not alert_summary[alert_type]['last_triggered'] or alert_date > alert_summary[alert_type]['last_triggered']:
                alert_summary[alert_type]['last_triggered'] = alert_date
                alert_summary[alert_type]['asset_id'] = alert.get('assetId', 'no-asset-id-assigned')
        
        return {
            'total_alerts': total_alerts,
            'alert_types': alert_summary,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_alerts_by_asset_id(self, asset_id: str) -> List[Dict]:
        """Get alerts filtered by asset ID"""
        return [alert for alert in self.alerts if alert.get('assetId') == asset_id]
    
    def get_asset_id_stats(self) -> Dict:
        """Get statistics about asset ID assignments"""
        stats = defaultdict(int)
        asset_id_alerts = defaultdict(list)
        
        for alert in self.alerts:
            asset_id = alert.get('assetId', 'no-asset-id-assigned')
            alert_type = alert.get('AlertType', 'Unknown')
            
            stats[asset_id] += 1
            asset_id_alerts[asset_id].append(alert_type)
        
        return {
            'total_alerts': len(self.alerts),
            'assigned_alerts': sum(count for asset_id, count in stats.items() if asset_id != 'no-asset-id-assigned'),
            'unassigned_alerts': stats.get('no-asset-id-assigned', 0),
            'asset_id_breakdown': dict(stats),
            'asset_id_alert_types': {asset_id: list(set(alert_types)) 
                                   for asset_id, alert_types in asset_id_alerts.items()},
            'assignment_rate': round((sum(count for asset_id, count in stats.items() 
                                        if asset_id != 'no-asset-id-assigned') / max(1, len(self.alerts))) * 100, 2)
        }
    
    def clear_old_alerts(self, days: int = 7):
        """Clear alerts older than specified days"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        original_count = len(self.alerts)
        
        self.alerts = deque([
            alert for alert in self.alerts 
            if datetime.fromisoformat(alert['Date'].replace('Z', '+00:00')) > cutoff_time
        ], maxlen=1000)
        
        cleared_count = original_count - len(self.alerts)
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} alerts older than {days} days")
        
        return cleared_count
    
    def export_alerts_for_asset(self, asset_id: str, format: str = 'json') -> Dict:
        """Export alerts for a specific asset ID"""
        asset_alerts = self.get_alerts_by_asset_id(asset_id)
        
        export_data = {
            'asset_id': asset_id,
            'total_alerts': len(asset_alerts),
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'alerts': asset_alerts
        }
        
        if format == 'summary':
            # Create summary format
            alert_types = defaultdict(int)
            priorities = defaultdict(int)
            
            for alert in asset_alerts:
                alert_types[alert.get('AlertType', 'Unknown')] += 1
                priorities[alert.get('Priority', 'Unknown')] += 1
            
            export_data['summary'] = {
                'alert_types': dict(alert_types),
                'priorities': dict(priorities),
                'date_range': {
                    'earliest': min([alert['Date'] for alert in asset_alerts]) if asset_alerts else None,
                    'latest': max([alert['Date'] for alert in asset_alerts]) if asset_alerts else None
                }
            }
        
        return export_data
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class SensorReading(BaseModel):
    sensor_type: str
    sensor_id: str
    assetId: str
    timestamp: str
    status: str
    data: Dict[str, Any]

class AlertConfig(BaseModel):
    alert_type: str
    enabled: bool = True
    threshold_value: Optional[float] = None
    cooldown_minutes: int = 5
    priority: str = "Medium"
    description_template: str = ""
    zone_id: Optional[str] = None

class AlertConfigUpdate(BaseModel):
    alert_type: str
    config: Dict[str, Any]

class Alert(BaseModel):
    AlertType: str
    assetId: str
    Description: str
    Date: str
    Report: str
    App: str
    anchor: str
    Stage_x007b__x0023__x007d_: str
    Failure_x0020_Class: str
    id: str
    Priority: str
    OperatorNumber: str
    OperatorName: str
    ManagerName: str
    ManagerNumber: str
    GoogleDriveURL: str

class ApiResponse(BaseModel):
    data: List[Dict]
    shouldSubscribe: str

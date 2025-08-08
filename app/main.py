"""
Multi-Sensor IoT API Server for Raspberry Pi
Complete sensor monitoring system with alerts
"""

import time
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from threading import Thread, Lock
import logging
import asyncio
from collections import defaultdict, deque
import uvicorn
from database.db_config import db_manager

# Import our modules
from models.sensor_models import *
from sensors.sensor_manager import SensorManager
from api.alert_manager import AlertManager
from config.settings import ALERT_CONFIGURATIONS, SENSOR_CONFIG
from utils.websocket_manager import WebSocketManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
sensor_manager = SensorManager()
alert_manager = AlertManager()
websocket_manager = WebSocketManager()

# FastAPI app
app = FastAPI(
    title="IoT Sensor Monitoring System",
    description="Complete sensor monitoring with real-time alerts",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for headers
@app.middleware("http")
async def add_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["User-Agent"] = "SensorAPI/3.0"
    return response

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Send sensor data every 2 seconds
            sensor_data = sensor_manager.get_all_readings()
            alerts = alert_manager.get_recent_alerts()
            
            data = {
                "type": "sensor_update",
                "sensors": sensor_data,
                "alerts": alerts,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket_manager.send_data(data)
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# API Routes
@app.get("/api/sensors", response_class=PlainTextResponse)
async def get_all_sensors():
    """Get all sensor readings"""
    try:
        readings = sensor_manager.get_all_readings()
        response = ApiResponse(data=readings, shouldSubscribe="true")
        return PlainTextResponse(
            content=json.dumps(response.dict(), indent=2),
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.error(f"Error getting sensors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensors/{sensor_type}")
async def get_sensor(sensor_type: str):
    """Get specific sensor reading"""
    try:
        reading = sensor_manager.get_sensor_reading(sensor_type)
        if not reading:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_type} not found")
        
        response = ApiResponse(data=[reading], shouldSubscribe="true")
        return response.dict()
    except Exception as e:
        logger.error(f"Error getting sensor {sensor_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_alerts():
    """Get all alerts"""
    try:
        alerts = alert_manager.get_all_alerts()
        response = ApiResponse(data=alerts, shouldSubscribe="true")
        return response.dict()
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/config")
async def get_alert_configs():
    """Get alert configurations"""
    try:
        configs = alert_manager.get_alert_configs()
        response = ApiResponse(data=configs, shouldSubscribe="true")
        return response.dict()
    except Exception as e:
        logger.error(f"Error getting alert configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/config")
async def update_alert_config(config_update: AlertConfigUpdate):
    """Update alert configuration"""
    try:
        result = alert_manager.update_alert_config(
            config_update.alert_type,
            config_update.config
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error updating alert config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/summary")
async def get_alerts_summary():
    """Get alerts summary"""
    try:
        summary = alert_manager.get_alerts_summary()
        response = ApiResponse(data=[summary], shouldSubscribe="true")
        return response.dict()
    except Exception as e:
        logger.error(f"Error getting alerts summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard")
async def get_dashboard():
    """Get dashboard data with asset IDs from database"""
    try:
        # Check database connection
        db_available = await ensure_db_connection()
        
        # Get sensor readings (sync)
        sensor_readings = sensor_manager.get_all_readings()
        
        # Update asset IDs from database if available
        if db_available:
            for reading in sensor_readings:
                if 'sensor_id' in reading:
                    try:
                        asset_id = await db_manager.get_sensor_asset_id(reading['sensor_id'])
                        reading['assetId'] = asset_id
                    except Exception as e:
                        logger.warning(f"Could not get asset ID for {reading['sensor_id']}: {e}")
                        reading['assetId'] = 'no-asset-id-assigned'
        else:
            # Fallback to default asset IDs
            for reading in sensor_readings:
                reading['assetId'] = reading.get('assetId', 'no-asset-id-assigned')
        
        # Get recent alerts
        recent_alerts = alert_manager.get_recent_alerts(limit=10)
        
        # Update alert asset IDs from database if available
        if db_available:
            for alert in recent_alerts:
                if 'AlertType' in alert:
                    try:
                        asset_id = await db_manager.get_alert_asset_id(alert['AlertType'])
                        alert['assetId'] = asset_id
                    except Exception as e:
                        logger.warning(f"Could not get asset ID for alert {alert['AlertType']}: {e}")
                        alert['assetId'] = 'no-asset-id-assigned'
        
        dashboard_data = {
            "sensors": sensor_readings,
            "alerts": recent_alerts,
            "summary": alert_manager.get_alerts_summary(),
            "system_status": sensor_manager.get_system_status(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = ApiResponse(data=[dashboard_data], shouldSubscribe="true")
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

async def ensure_db_connection():
    """Ensure database connection is available"""
    try:
        if not db_manager.connection_pool:
            await db_manager.initialize()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

@app.get("/api/asset-ids")
async def get_asset_ids():
    """Get all asset IDs"""
    try:
        asset_ids = await db_manager.get_asset_ids()
        return {"data": asset_ids}
    except Exception as e:
        logger.error(f"Error getting asset IDs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/asset-ids")
async def add_asset_id(request: dict):
    """Add new asset ID"""
    try:
        assetid = request.get("assetid")
        if not assetid:
            raise HTTPException(status_code=400, detail="assetid is required")
        
        result = await db_manager.add_asset_id(assetid)
        return {"data": result}
    except Exception as e:
        logger.error(f"Error adding asset ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/asset-ids")
async def update_asset_id(request: dict):
    """Update asset ID"""
    try:
        id = request.get("id")
        assetid = request.get("assetid")
        if not id or not assetid:
            raise HTTPException(status_code=400, detail="id and assetid are required")
        
        success = await db_manager.update_asset_id(id, assetid)
        if not success:
            raise HTTPException(status_code=404, detail="Asset ID not found")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error updating asset ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/asset-ids")
async def delete_asset_id(request: dict):
    """Delete asset ID"""
    try:
        id = request.get("id")
        if not id:
            raise HTTPException(status_code=400, detail="id is required")
        
        success = await db_manager.delete_asset_id(id)
        if not success:
            raise HTTPException(status_code=404, detail="Asset ID not found")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting asset ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensors-to-asset-ids")
async def get_sensors_to_asset_ids():
    """Get sensor to asset ID mappings"""
    try:
        mappings = await db_manager.get_sensors_to_asset_ids()
        return {"data": mappings}
    except Exception as e:
        logger.error(f"Error getting sensor mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sensors-to-asset-ids")
async def add_sensor_to_asset_id(request: dict):
    """Add sensor to asset ID mapping"""
    try:
        sensor_name = request.get("sensorName")
        assetids = request.get("assetids")
        if not sensor_name:
            raise HTTPException(status_code=400, detail="sensorName is required")
        
        result = await db_manager.upsert_sensor_to_asset_id(sensor_name, assetids)
        return {"data": result}
    except Exception as e:
        logger.error(f"Error adding sensor mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/sensors-to-asset-ids")
async def update_sensor_to_asset_id(request: dict):
    """Update sensor to asset ID mapping"""
    try:
        sensor_name = request.get("sensorName")
        assetids = request.get("assetids")
        if not sensor_name:
            raise HTTPException(status_code=400, detail="sensorName is required")
        
        result = await db_manager.upsert_sensor_to_asset_id(sensor_name, assetids)
        return {"data": result}
    except Exception as e:
        logger.error(f"Error updating sensor mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sensors-to-asset-ids")
async def delete_sensor_to_asset_id(request: dict):
    """Delete sensor to asset ID mapping"""
    try:
        id = request.get("id")
        if not id:
            raise HTTPException(status_code=400, detail="id is required")
        
        success = await db_manager.delete_sensor_to_asset_id(id)
        if not success:
            raise HTTPException(status_code=404, detail="Sensor mapping not found")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting sensor mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts-to-asset-ids")
async def get_alerts_to_asset_ids():
    """Get alert to asset ID mappings"""
    try:
        mappings = await db_manager.get_alerts_to_asset_ids()
        return {"data": mappings}
    except Exception as e:
        logger.error(f"Error getting alert mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts-to-asset-ids")
async def add_alert_to_asset_id(request: dict):
    """Add alert to asset ID mapping"""
    try:
        alert_type = request.get("alertType")
        assetids = request.get("assetids")
        if not alert_type:
            raise HTTPException(status_code=400, detail="alertType is required")
        
        result = await db_manager.upsert_alert_to_asset_id(alert_type, assetids)
        return {"data": result}
    except Exception as e:
        logger.error(f"Error adding alert mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/alerts-to-asset-ids")
async def update_alert_to_asset_id(request: dict):
    """Update alert to asset ID mapping"""
    try:
        alert_type = request.get("alertType")
        assetids = request.get("assetids")
        if not alert_type:
            raise HTTPException(status_code=400, detail="alertType is required")
        
        result = await db_manager.upsert_alert_to_asset_id(alert_type, assetids)
        return {"data": result}
    except Exception as e:
        logger.error(f"Error updating alert mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/alerts-to-asset-ids")
async def delete_alert_to_asset_id(request: dict):
    """Delete alert to asset ID mapping"""
    try:
        id = request.get("id")
        if not id:
            raise HTTPException(status_code=400, detail="id is required")
        
        success = await db_manager.delete_alert_to_asset_id(id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert mapping not found")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting alert mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        health = sensor_manager.get_health_status()
        return {"status": "healthy", "sensors": health}
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "unhealthy", "error": str(e)}

def background_sensor_loop():
    """Background task for continuous sensor readings"""
    while True:
        try:
            # Update all sensors
            sensor_manager.update_all_sensors()
            
            # Check for alerts
            alert_manager.check_all_alerts(sensor_manager.get_all_readings())
            
            time.sleep(1)  # Update every second
        except Exception as e:
            logger.error(f"Background loop error: {e}")
            time.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    try:
        # Try to initialize database
        await db_manager.initialize()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Continuing without database - asset IDs will use defaults")
    
    # Start background sensor reading
    sensor_thread = Thread(target=background_sensor_loop, daemon=True)
    sensor_thread.start()
    
    logger.info("Sensor monitoring system started")
    logger.info(f"Available sensors: {list(sensor_manager.sensors.keys())}")
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db_manager.close()
    sensor_manager.cleanup()
    logger.info("Sensor monitoring system stopped")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

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
    """Get dashboard data"""
    try:
        dashboard_data = {
            "sensors": sensor_manager.get_all_readings(),
            "alerts": alert_manager.get_recent_alerts(limit=10),
            "summary": alert_manager.get_alerts_summary(),
            "system_status": sensor_manager.get_system_status(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = ApiResponse(data=[dashboard_data], shouldSubscribe="true")
        return response.dict()
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
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
    # Start background sensor reading
    sensor_thread = Thread(target=background_sensor_loop, daemon=True)
    sensor_thread.start()
    
    logger.info("Sensor monitoring system started")
    logger.info(f"Available sensors: {list(sensor_manager.sensors.keys())}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    sensor_manager.cleanup()
    logger.info("Sensor monitoring system stopped")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

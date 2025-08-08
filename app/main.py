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

 

@app.get("/api/asset-ids")
async def get_asset_ids():
    """Get all asset IDs"""
    try:
        asset_ids = await db_manager.get_asset_ids()
        return {"data": asset_ids}
    except Exception as e:
        logger.error(f"Error getting asset IDs: {e}")
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

# Add these enhanced endpoints to your main.py

@app.get("/api/sensors", response_class=PlainTextResponse)
async def get_all_sensors():
    """Get all sensor readings with proper asset ID assignment"""
    try:
        # Check database connection
        db_available = await ensure_db_connection()
        
        # Get sensor readings (sync)
        readings = sensor_manager.get_all_readings()
        
        # Update asset IDs from database if available
        if db_available:
            for reading in readings:
                if 'sensor_id' in reading:
                    try:
                        asset_id = await db_manager.get_sensor_asset_id(reading['sensor_id'])
                        reading['assetId'] = asset_id
                        logger.debug(f"Assigned asset ID '{asset_id}' to sensor '{reading['sensor_id']}'")
                    except Exception as e:
                        logger.warning(f"Could not get asset ID for {reading['sensor_id']}: {e}")
                        reading['assetId'] = 'no-asset-id-assigned'
        else:
            # Fallback to default asset IDs
            for reading in readings:
                reading['assetId'] = reading.get('assetId', 'no-asset-id-assigned')
        
        response = ApiResponse(data=readings, shouldSubscribe="true")
        return PlainTextResponse(
            content=json.dumps(response.dict(), indent=2),
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.error(f"Error getting sensors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_alerts():
    """Get all alerts with proper asset ID assignment"""
    try:
        # Check database connection
        db_available = await ensure_db_connection()
        
        # Get alerts
        alerts = alert_manager.get_all_alerts()
        
        # Update alert asset IDs from database if available
        if db_available:
            for alert in alerts:
                if 'AlertType' in alert:
                    try:
                        asset_id = await db_manager.get_alert_asset_id(alert['AlertType'])
                        alert['assetId'] = asset_id
                        logger.debug(f"Assigned asset ID '{asset_id}' to alert '{alert['AlertType']}'")
                    except Exception as e:
                        logger.warning(f"Could not get asset ID for alert {alert['AlertType']}: {e}")
                        alert['assetId'] = 'no-asset-id-assigned'
        else:
            # Fallback to default asset IDs
            for alert in alerts:
                alert['assetId'] = alert.get('assetId', 'no-asset-id-assigned')
        
        response = ApiResponse(data=alerts, shouldSubscribe="true")
        return response.dict()
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
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
        recent_alerts = alert_manager.get_recent_alerts(limit=50)
        
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_available": db_available
        }
        
        response = ApiResponse(data=[dashboard_data], shouldSubscribe="true")
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced asset ID management endpoints with better validation
@app.post("/api/asset-ids")
async def add_asset_id(request: dict):
    """Add new asset ID with validation"""
    try:
        assetid = request.get("assetid", "").strip()
        if not assetid:
            raise HTTPException(status_code=400, detail="assetid is required and cannot be empty")
        
        if len(assetid) > 255:
            raise HTTPException(status_code=400, detail="assetid cannot be longer than 255 characters")
        
        result = await db_manager.upsert_sensor_to_asset_id(sensor_name, assetids)
        
        # Clear cache to ensure fresh data
        await db_manager.clear_cache()
        
        logger.info(f"Sensor '{sensor_name}' mapping updated successfully")
        return {"data": result, "message": f"Sensor mapping updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating sensor mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts-to-asset-ids")
async def add_alert_to_asset_id(request: dict):
    """Add/update alert to asset ID mapping with validation"""
    try:
        alert_type = request.get("alertType", "").strip()
        assetids = request.get("assetids", "").strip()
        
        if not alert_type:
            raise HTTPException(status_code=400, detail="alertType is required")
        
        if assetids and len(assetids) > 255:
            raise HTTPException(status_code=400, detail="assetids cannot be longer than 255 characters")
        
        result = await db_manager.upsert_alert_to_asset_id(alert_type, assetids)
        
        # Clear cache to ensure fresh data
        await db_manager.clear_cache()
        
        logger.info(f"Alert '{alert_type}' mapped to asset ID '{assetids}' successfully")
        return {"data": result, "message": f"Alert mapping updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding alert mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/alerts-to-asset-ids")
async def update_alert_to_asset_id(request: dict):
    """Update alert to asset ID mapping"""
    try:
        alert_type = request.get("alertType", "").strip()
        assetids = request.get("assetids", "").strip()
        
        if not alert_type:
            raise HTTPException(status_code=400, detail="alertType is required")
        
        if assetids and len(assetids) > 255:
            raise HTTPException(status_code=400, detail="assetids cannot be longer than 255 characters")
        
        result = await db_manager.upsert_alert_to_asset_id(alert_type, assetids)
        
        # Clear cache to ensure fresh data
        await db_manager.clear_cache()
        
        logger.info(f"Alert '{alert_type}' mapping updated successfully")
        return {"data": result, "message": f"Alert mapping updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating alert mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Debug and monitoring endpoints
@app.get("/api/debug/asset-assignments")
async def get_debug_asset_assignments():
    """Debug endpoint to see all asset assignments"""
    try:
        db_available = await ensure_db_connection()
        
        if not db_available:
            return {"error": "Database not available", "database_available": False}
        
        # Get all mappings
        asset_ids = await db_manager.get_asset_ids()
        sensor_mappings = await db_manager.get_sensors_to_asset_ids()
        alert_mappings = await db_manager.get_alerts_to_asset_ids()
        
        # Get current sensor readings with asset IDs
        sensor_readings = sensor_manager.get_all_readings()
        for reading in sensor_readings:
            if 'sensor_id' in reading:
                asset_id = await db_manager.get_sensor_asset_id(reading['sensor_id'])
                reading['resolved_asset_id'] = asset_id
        
        # Get cache stats
        cache_stats = await db_manager.get_cache_stats()
        
        return {
            "database_available": True,
            "asset_ids": asset_ids,
            "sensor_mappings": sensor_mappings,
            "alert_mappings": alert_mappings,
            "current_sensor_assignments": [
                {
                    "sensor_id": r.get('sensor_id'),
                    "sensor_type": r.get('sensor_type'),
                    "resolved_asset_id": r.get('resolved_asset_id'),
                    "status": r.get('status')
                } for r in sensor_readings
            ],
            "cache_stats": cache_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting debug asset assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/debug/clear-cache")
async def clear_asset_cache():
    """Clear the asset ID cache"""
    try:
        await db_manager.clear_cache()
        return {"message": "Asset ID cache cleared successfully", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/database-status")
async def get_database_status():
    """Get detailed database connection status"""
    try:
        db_available = await ensure_db_connection()
        
        if db_available:
            # Test database operations
            asset_count = len(await db_manager.get_asset_ids())
            sensor_mapping_count = len(await db_manager.get_sensors_to_asset_ids())
            alert_mapping_count = len(await db_manager.get_alerts_to_asset_ids())
            cache_stats = await db_manager.get_cache_stats()
            
            return {
                "database_available": True,
                "connection_pool_available": db_manager.connection_pool is not None,
                "asset_ids_count": asset_count,
                "sensor_mappings_count": sensor_mapping_count,
                "alert_mappings_count": alert_mapping_count,
                "cache_stats": cache_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "database_available": False,
                "connection_pool_available": False,
                "error": "Database connection not available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        return {
            "database_available": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Enhanced ensure_db_connection function
async def ensure_db_connection():
    """Ensure database connection is available with retry logic"""
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            if not db_manager.connection_pool:
                logger.info(f"Database connection attempt {attempt + 1}/{max_retries}")
                await db_manager.initialize()
            
            # Test the connection
            if await db_manager.verify_connection():
                return True
                
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Database connection failed after {max_retries} attempts")
    
    return False

# WebSocket enhancement to include asset IDs
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Check database connection
            db_available = await ensure_db_connection()
            
            # Get sensor data with asset IDs
            sensor_data = sensor_manager.get_all_readings()
            
            # Update asset IDs from database if available
            if db_available:
                for reading in sensor_data:
                    if 'sensor_id' in reading:
                        try:
                            asset_id = await db_manager.get_sensor_asset_id(reading['sensor_id'])
                            reading['assetId'] = asset_id
                        except Exception:
                            reading['assetId'] = 'no-asset-id-assigned'
            
            # Get alerts with asset IDs
            alerts = alert_manager.get_recent_alerts()
            
            if db_available:
                for alert in alerts:
                    if 'AlertType' in alert:
                        try:
                            asset_id = await db_manager.get_alert_asset_id(alert['AlertType'])
                            alert['assetId'] = asset_id
                        except Exception:
                            alert['assetId'] = 'no-asset-id-assigned'
            
            data = {
                "type": "sensor_update",
                "sensors": sensor_data,
                "alerts": alerts,
                "database_available": db_available,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket_manager.send_data(data)
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket) = await db_manager.add_asset_id(assetid)
        
        # Clear cache to ensure fresh data
        await db_manager.clear_cache()
        
        logger.info(f"Asset ID '{assetid}' added successfully")
        return {"data": result, "message": f"Asset ID '{assetid}' added successfully"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding asset ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/asset-ids")
async def update_asset_id(request: dict):
    """Update asset ID with validation"""
    try:
        id = request.get("id")
        assetid = request.get("assetid", "").strip()
        
        if not id:
            raise HTTPException(status_code=400, detail="id is required")
        if not assetid:
            raise HTTPException(status_code=400, detail="assetid is required and cannot be empty")
        if len(assetid) > 255:
            raise HTTPException(status_code=400, detail="assetid cannot be longer than 255 characters")
        
        success = await db_manager.update_asset_id(id, assetid)
        if not success:
            raise HTTPException(status_code=404, detail="Asset ID not found")
        
        # Clear cache to ensure fresh data
        await db_manager.clear_cache()
        
        logger.info(f"Asset ID {id} updated to '{assetid}' successfully")
        return {"success": True, "message": f"Asset ID updated to '{assetid}' successfully"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating asset ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sensors-to-asset-ids")
async def add_sensor_to_asset_id(request: dict):
    """Add/update sensor to asset ID mapping with validation"""
    try:
        sensor_name = request.get("sensorName", "").strip()
        assetids = request.get("assetids", "").strip()
        
        if not sensor_name:
            raise HTTPException(status_code=400, detail="sensorName is required")
        
        if assetids and len(assetids) > 255:
            raise HTTPException(status_code=400, detail="assetids cannot be longer than 255 characters")
        
        result = await db_manager.upsert_sensor_to_asset_id(sensor_name, assetids)
        
        # Clear cache to ensure fresh data
        await db_manager.clear_cache()
        
        logger.info(f"Sensor '{sensor_name}' mapped to asset ID '{assetids}' successfully")
        return {"data": result, "message": f"Sensor mapping updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding sensor mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/sensors-to-asset-ids")
async def update_sensor_to_asset_id(request: dict):
    """Update sensor to asset ID mapping"""
    try:
        sensor_name = request.get("sensorName", "").strip()
        assetids = request.get("assetids", "").strip()
        
        if not sensor_name:
            raise HTTPException(status_code=400, detail="sensorName is required")
        
        if assetids and len(assetids) > 255:
            raise HTTPException(status_code=400, detail="assetids cannot be longer than 255 characters")
        
        result = await db_manager.upsert_sensor_to_asset_id(sensor_name, assetids)
        # Clear cache to ensure fresh data
        await db_manager.clear_cache()
        logger.info(f"Sensor '{sensor_name}' mapping updated successfully")
        return {"data": result, "message": f"Sensor mapping updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating sensor mapping: {e}")
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

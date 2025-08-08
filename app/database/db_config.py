import os
import asyncpg
import asyncio
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://neondb_owner:npg_12wIbYzPpQaj@ep-morning-feather-a1l0mfdr-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

class DatabaseManager:
    def __init__(self):
        self.connection_pool = None
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self):
        """Create tables if they don't exist"""
        async with self.connection_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "assetIds" (
                    id SERIAL PRIMARY KEY,
                    assetid VARCHAR(255) NOT NULL
                );
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "sensorsToAssetIds" (
                    id SERIAL PRIMARY KEY,
                    "sensorName" VARCHAR(255) NOT NULL,
                    assetids VARCHAR(255)
                );
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "alertsToAssetIds" (
                    id SERIAL PRIMARY KEY,
                    "alertType" VARCHAR(255) NOT NULL,
                    assetids VARCHAR(255)
                );
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "userDetailsWhoDownloadPdf" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
                );
            ''')
            
            logger.info("Database tables created/verified")
    
    async def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connection pool closed")
    
    # Asset IDs
    async def get_asset_ids(self) -> List[Dict]:
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, assetid FROM "assetIds" ORDER BY id')
            return [dict(row) for row in rows]
    
    async def add_asset_id(self, assetid: str) -> Dict:
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                'INSERT INTO "assetIds" (assetid) VALUES ($1) RETURNING id, assetid',
                assetid
            )
            return dict(row)
    
    async def update_asset_id(self, id: int, assetid: str) -> bool:
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE "assetIds" SET assetid = $1 WHERE id = $2',
                assetid, id
            )
            return result == "UPDATE 1"
    
    async def delete_asset_id(self, id: int) -> bool:
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute('DELETE FROM "assetIds" WHERE id = $1', id)
            return result == "DELETE 1"
    
    # Sensors to Asset IDs
    async def get_sensors_to_asset_ids(self) -> List[Dict]:
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, "sensorName", assetids FROM "sensorsToAssetIds" ORDER BY id')
            return [dict(row) for row in rows]
    
    async def upsert_sensor_to_asset_id(self, sensor_name: str, assetids: str) -> Dict:
        async with self.connection_pool.acquire() as conn:
            # Try to update first
            result = await conn.execute(
                'UPDATE "sensorsToAssetIds" SET assetids = $1 WHERE "sensorName" = $2',
                assetids, sensor_name
            )
            
            if result == "UPDATE 0":
                # Insert if update didn't affect any rows
                row = await conn.fetchrow(
                    'INSERT INTO "sensorsToAssetIds" ("sensorName", assetids) VALUES ($1, $2) RETURNING id, "sensorName", assetids',
                    sensor_name, assetids
                )
                return dict(row)
            else:
                # Return updated row
                row = await conn.fetchrow(
                    'SELECT id, "sensorName", assetids FROM "sensorsToAssetIds" WHERE "sensorName" = $1',
                    sensor_name
                )
                return dict(row)
    
    async def delete_sensor_to_asset_id(self, id: int) -> bool:
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute('DELETE FROM "sensorsToAssetIds" WHERE id = $1', id)
            return result == "DELETE 1"
    
    # Alerts to Asset IDs
    async def get_alerts_to_asset_ids(self) -> List[Dict]:
        async with self.connection_pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, "alertType", assetids FROM "alertsToAssetIds" ORDER BY id')
            return [dict(row) for row in rows]
    
    async def upsert_alert_to_asset_id(self, alert_type: str, assetids: str) -> Dict:
        async with self.connection_pool.acquire() as conn:
            # Try to update first
            result = await conn.execute(
                'UPDATE "alertsToAssetIds" SET assetids = $1 WHERE "alertType" = $2',
                assetids, alert_type
            )
            
            if result == "UPDATE 0":
                # Insert if update didn't affect any rows
                row = await conn.fetchrow(
                    'INSERT INTO "alertsToAssetIds" ("alertType", assetids) VALUES ($1, $2) RETURNING id, "alertType", assetids',
                    alert_type, assetids
                )
                return dict(row)
            else:
                # Return updated row
                row = await conn.fetchrow(
                    'SELECT id, "alertType", assetids FROM "alertsToAssetIds" WHERE "alertType" = $1',
                    alert_type
                )
                return dict(row)
    
    async def delete_alert_to_asset_id(self, id: int) -> bool:
        async with self.connection_pool.acquire() as conn:
            result = await conn.execute('DELETE FROM "alertsToAssetIds" WHERE id = $1', id)
            return result == "DELETE 1"
    
    async def get_sensor_asset_id(self, sensor_name: str) -> str:
        """Get asset ID for a sensor, return 'no-asset-id-assigned' if not found"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT assetids FROM "sensorsToAssetIds" WHERE "sensorName" = $1',
                sensor_name
            )
            return row['assetids'] if row and row['assetids'] else 'no-asset-id-assigned'
    
    async def get_alert_asset_id(self, alert_type: str) -> str:
        """Get asset ID for an alert type, return 'no-asset-id-assigned' if not found"""
        async with self.connection_pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT assetids FROM "alertsToAssetIds" WHERE "alertType" = $1',
                alert_type
            )
            return row['assetids'] if row and row['assetids'] else 'no-asset-id-assigned'

# Global database manager instance
db_manager = DatabaseManager()
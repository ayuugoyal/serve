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
        self._connection_timeout = 10.0
        self._query_timeout = 5.0
        
    async def initialize(self):
        """Initialize database connection pool with better error handling"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=self._query_timeout,
                server_settings={
                    'application_name': 'iot_sensor_system',
                    'tcp_keepalives_idle': '300',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3'
                }
            )
            logger.info("Database connection pool initialized successfully")
            await self.create_tables()
            await self.verify_connection()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def verify_connection(self):
        """Verify database connection is working"""
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                result = await asyncio.wait_for(
                    conn.fetchval('SELECT 1'),
                    timeout=self._query_timeout
                )
                logger.info("Database connection verified successfully")
                return True
        except Exception as e:
            logger.error(f"Database connection verification failed: {e}")
            return False
    
    async def create_tables(self):
        """Create tables if they don't exist with better constraints"""
        async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
            # Create assetIds table with unique constraint
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "assetIds" (
                    id SERIAL PRIMARY KEY,
                    assetid VARCHAR(255) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create index on assetid for faster lookups
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_assetids_assetid ON "assetIds" (assetid);
            ''')
            
            # Create sensorsToAssetIds table with unique sensor constraint
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "sensorsToAssetIds" (
                    id SERIAL PRIMARY KEY,
                    "sensorName" VARCHAR(255) NOT NULL UNIQUE,
                    assetids VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create index on sensorName for faster lookups
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_sensors_to_assetids_sensorname ON "sensorsToAssetIds" ("sensorName");
            ''')
            
            # Create alertsToAssetIds table with unique alert type constraint
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "alertsToAssetIds" (
                    id SERIAL PRIMARY KEY,
                    "alertType" VARCHAR(255) NOT NULL UNIQUE,
                    assetids VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create index on alertType for faster lookups
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_to_assetids_alerttype ON "alertsToAssetIds" ("alertType");
            ''')
            
            # Create userDetailsWhoDownloadPdf table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS "userDetailsWhoDownloadPdf" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
                );
            ''')
            
            # Create trigger to update updated_at timestamp
            await conn.execute('''
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            ''')
            
            # Add triggers for automatic timestamp updates
            for table in ['"assetIds"', '"sensorsToAssetIds"', '"alertsToAssetIds"']:
                await conn.execute(f'''
                    DROP TRIGGER IF EXISTS update_{table.replace('"', '')}_updated_at ON {table};
                    CREATE TRIGGER update_{table.replace('"', '')}_updated_at
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                ''')
            
            logger.info("Database tables created/verified with indexes and triggers")
    
    async def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database connection pool closed")
    
    # Asset IDs with better error handling
    async def get_asset_ids(self) -> List[Dict]:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                rows = await asyncio.wait_for(
                    conn.fetch('SELECT id, assetid, created_at, updated_at FROM "assetIds" ORDER BY id'),
                    timeout=self._query_timeout
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching asset IDs: {e}")
            return []
    
    async def add_asset_id(self, assetid: str) -> Dict:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                row = await asyncio.wait_for(
                    conn.fetchrow(
                        'INSERT INTO "assetIds" (assetid) VALUES ($1) RETURNING id, assetid, created_at, updated_at',
                        assetid.strip()
                    ),
                    timeout=self._query_timeout
                )
                logger.info(f"Added asset ID: {assetid}")
                return dict(row)
        except asyncpg.UniqueViolationError:
            logger.warning(f"Asset ID '{assetid}' already exists")
            raise ValueError(f"Asset ID '{assetid}' already exists")
        except Exception as e:
            logger.error(f"Error adding asset ID '{assetid}': {e}")
            raise
    
    async def update_asset_id(self, id: int, assetid: str) -> bool:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                result = await asyncio.wait_for(
                    conn.execute(
                        'UPDATE "assetIds" SET assetid = $1 WHERE id = $2',
                        assetid.strip(), id
                    ),
                    timeout=self._query_timeout
                )
                success = result == "UPDATE 1"
                if success:
                    logger.info(f"Updated asset ID {id} to '{assetid}'")
                return success
        except asyncpg.UniqueViolationError:
            logger.warning(f"Asset ID '{assetid}' already exists")
            raise ValueError(f"Asset ID '{assetid}' already exists")
        except Exception as e:
            logger.error(f"Error updating asset ID {id}: {e}")
            raise
    
    async def delete_asset_id(self, id: int) -> bool:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                # First, get the asset ID for logging
                asset_row = await conn.fetchrow('SELECT assetid FROM "assetIds" WHERE id = $1', id)
                if not asset_row:
                    return False
                
                # Remove references in other tables
                await conn.execute('UPDATE "sensorsToAssetIds" SET assetids = NULL WHERE assetids = $1', asset_row['assetid'])
                await conn.execute('UPDATE "alertsToAssetIds" SET assetids = NULL WHERE assetids = $1', asset_row['assetid'])
                
                # Delete the asset ID
                result = await asyncio.wait_for(
                    conn.execute('DELETE FROM "assetIds" WHERE id = $1', id),
                    timeout=self._query_timeout
                )
                success = result == "DELETE 1"
                if success:
                    logger.info(f"Deleted asset ID {id} ({asset_row['assetid']}) and cleared references")
                return success
        except Exception as e:
            logger.error(f"Error deleting asset ID {id}: {e}")
            raise
    
    # Sensors to Asset IDs with better error handling
    async def get_sensors_to_asset_ids(self) -> List[Dict]:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                rows = await asyncio.wait_for(
                    conn.fetch('SELECT id, "sensorName", assetids, created_at, updated_at FROM "sensorsToAssetIds" ORDER BY id'),
                    timeout=self._query_timeout
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching sensor to asset ID mappings: {e}")
            return []
    
    async def upsert_sensor_to_asset_id(self, sensor_name: str, assetids: str) -> Dict:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                # Validate asset ID exists if provided
                if assetids and assetids.strip():
                    asset_exists = await conn.fetchval('SELECT 1 FROM "assetIds" WHERE assetid = $1', assetids.strip())
                    if not asset_exists:
                        raise ValueError(f"Asset ID '{assetids}' does not exist")
                
                # Use ON CONFLICT for atomic upsert
                row = await asyncio.wait_for(
                    conn.fetchrow('''
                        INSERT INTO "sensorsToAssetIds" ("sensorName", assetids) 
                        VALUES ($1, $2)
                        ON CONFLICT ("sensorName") 
                        DO UPDATE SET assetids = $2, updated_at = CURRENT_TIMESTAMP
                        RETURNING id, "sensorName", assetids, created_at, updated_at
                    ''', sensor_name.strip(), assetids.strip() if assetids else None),
                    timeout=self._query_timeout
                )
                logger.info(f"Upserted sensor '{sensor_name}' with asset ID '{assetids}'")
                return dict(row)
        except Exception as e:
            logger.error(f"Error upserting sensor to asset ID mapping: {e}")
            raise
    
    async def delete_sensor_to_asset_id(self, id: int) -> bool:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                result = await asyncio.wait_for(
                    conn.execute('DELETE FROM "sensorsToAssetIds" WHERE id = $1', id),
                    timeout=self._query_timeout
                )
                success = result == "DELETE 1"
                if success:
                    logger.info(f"Deleted sensor to asset ID mapping {id}")
                return success
        except Exception as e:
            logger.error(f"Error deleting sensor to asset ID mapping {id}: {e}")
            raise
    
    # Alerts to Asset IDs with better error handling
    async def get_alerts_to_asset_ids(self) -> List[Dict]:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                rows = await asyncio.wait_for(
                    conn.fetch('SELECT id, "alertType", assetids, created_at, updated_at FROM "alertsToAssetIds" ORDER BY id'),
                    timeout=self._query_timeout
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching alert to asset ID mappings: {e}")
            return []
    
    async def upsert_alert_to_asset_id(self, alert_type: str, assetids: str) -> Dict:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                # Validate asset ID exists if provided
                if assetids and assetids.strip():
                    asset_exists = await conn.fetchval('SELECT 1 FROM "assetIds" WHERE assetid = $1', assetids.strip())
                    if not asset_exists:
                        raise ValueError(f"Asset ID '{assetids}' does not exist")
                
                # Use ON CONFLICT for atomic upsert
                row = await asyncio.wait_for(
                    conn.fetchrow('''
                        INSERT INTO "alertsToAssetIds" ("alertType", assetids) 
                        VALUES ($1, $2)
                        ON CONFLICT ("alertType") 
                        DO UPDATE SET assetids = $2, updated_at = CURRENT_TIMESTAMP
                        RETURNING id, "alertType", assetids, created_at, updated_at
                    ''', alert_type.strip(), assetids.strip() if assetids else None),
                    timeout=self._query_timeout
                )
                logger.info(f"Upserted alert '{alert_type}' with asset ID '{assetids}'")
                return dict(row)
        except Exception as e:
            logger.error(f"Error upserting alert to asset ID mapping: {e}")
            raise
    
    async def delete_alert_to_asset_id(self, id: int) -> bool:
        try:
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                result = await asyncio.wait_for(
                    conn.execute('DELETE FROM "alertsToAssetIds" WHERE id = $1', id),
                    timeout=self._query_timeout
                )
                success = result == "DELETE 1"
                if success:
                    logger.info(f"Deleted alert to asset ID mapping {id}")
                return success
        except Exception as e:
            logger.error(f"Error deleting alert to asset ID mapping {id}: {e}")
            raise
    
    # Enhanced lookup methods with caching
    _sensor_cache = {}
    _alert_cache = {}
    _cache_ttl = 60  # 60 seconds
    _last_cache_update = 0
    
    async def get_sensor_asset_id(self, sensor_name: str) -> str:
        """Get asset ID for a sensor with caching, return 'no-asset-id-assigned' if not found"""
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Refresh cache if needed
            if current_time - self._last_cache_update > self._cache_ttl:
                await self._refresh_cache()
            
            # Check cache first
            if sensor_name in self._sensor_cache:
                return self._sensor_cache[sensor_name] or 'no-asset-id-assigned'
            
            # Fallback to direct database query
            if not self.connection_pool:
                return 'no-asset-id-assigned'
                
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                row = await asyncio.wait_for(
                    conn.fetchrow('SELECT assetids FROM "sensorsToAssetIds" WHERE "sensorName" = $1', sensor_name),
                    timeout=self._query_timeout
                )
                result = row['assetids'] if row and row['assetids'] else 'no-asset-id-assigned'
                
                # Update cache
                self._sensor_cache[sensor_name] = result
                return result
                
        except Exception as e:
            logger.warning(f"Database query failed for sensor {sensor_name}: {e}")
            return 'no-asset-id-assigned'

    async def get_alert_asset_id(self, alert_type: str) -> str:
        """Get asset ID for an alert type with caching, return 'no-asset-id-assigned' if not found"""
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Refresh cache if needed
            if current_time - self._last_cache_update > self._cache_ttl:
                await self._refresh_cache()
            
            # Check cache first
            if alert_type in self._alert_cache:
                return self._alert_cache[alert_type] or 'no-asset-id-assigned'
            
            # Fallback to direct database query
            if not self.connection_pool:
                return 'no-asset-id-assigned'
                
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                row = await asyncio.wait_for(
                    conn.fetchrow('SELECT assetids FROM "alertsToAssetIds" WHERE "alertType" = $1', alert_type),
                    timeout=self._query_timeout
                )
                result = row['assetids'] if row and row['assetids'] else 'no-asset-id-assigned'
                
                # Update cache
                self._alert_cache[alert_type] = result
                return result
                
        except Exception as e:
            logger.warning(f"Database query failed for alert {alert_type}: {e}")
            return 'no-asset-id-assigned'
    
    async def _refresh_cache(self):
        """Refresh the asset ID cache"""
        try:
            if not self.connection_pool:
                return
                
            async with asyncio.wait_for(self.connection_pool.acquire(), timeout=self._connection_timeout) as conn:
                # Refresh sensor cache
                sensor_rows = await asyncio.wait_for(
                    conn.fetch('SELECT "sensorName", assetids FROM "sensorsToAssetIds"'),
                    timeout=self._query_timeout
                )
                self._sensor_cache = {row['sensorName']: row['assetids'] for row in sensor_rows}
                
                # Refresh alert cache
                alert_rows = await asyncio.wait_for(
                    conn.fetch('SELECT "alertType", assetids FROM "alertsToAssetIds"'),
                    timeout=self._query_timeout
                )
                self._alert_cache = {row['alertType']: row['assetids'] for row in alert_rows}
                
                self._last_cache_update = asyncio.get_event_loop().time()
                logger.debug("Asset ID cache refreshed")
                
        except Exception as e:
            logger.warning(f"Failed to refresh cache: {e}")
    
    async def clear_cache(self):
        """Clear the asset ID cache"""
        self._sensor_cache.clear()
        self._alert_cache.clear()
        self._last_cache_update = 0
        logger.info("Asset ID cache cleared")
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        current_time = asyncio.get_event_loop().time()
        cache_age = current_time - self._last_cache_update
        
        return {
            'sensor_cache_size': len(self._sensor_cache),
            'alert_cache_size': len(self._alert_cache),
            'cache_age_seconds': round(cache_age, 2),
            'cache_ttl_seconds': self._cache_ttl,
            'cache_expired': cache_age > self._cache_ttl
        }

# Global database manager instance
db_manager = DatabaseManager()
#!/usr/bin/env python3
"""
Database initialization script
Run this to set up the database tables and initial data
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from database.db_config import db_manager

async def initialize_database():
    """Initialize database with tables and sample data"""
    try:
        print("🔄 Initializing database connection...")
        await db_manager.initialize()
        
        print("✅ Database tables created successfully!")
        
        # Add some sample asset IDs
        sample_asset_ids = [
            "MCN-02",
            "SENSOR-ZONE-1", 
            "SENSOR-ZONE-2",
            "SENSOR-ZONE-3",
            "ALERT-SYSTEM-1"
        ]
        
        print("🔄 Adding sample asset IDs...")
        for asset_id in sample_asset_ids:
            try:
                await db_manager.add_asset_id(asset_id)
                print(f"  ✅ Added asset ID: {asset_id}")
            except Exception as e:
                print(f"  ⚠️ Asset ID {asset_id} may already exist: {e}")
        
        print("✅ Database initialization completed!")
        print("\n📊 Database is ready for IoT sensor system!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(initialize_database())
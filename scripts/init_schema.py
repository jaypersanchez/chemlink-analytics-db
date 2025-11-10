#!/usr/bin/env python3
"""
Initialize Analytics Database Schema
Executes all SQL schema files in order
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_config import get_analytics_db_connection

def execute_sql_file(conn, filepath):
    """Execute a SQL file"""
    print(f"\n{'='*70}")
    print(f"Executing: {os.path.basename(filepath)}")
    print(f"{'='*70}")
    
    with open(filepath, 'r') as f:
        sql = f.read()
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
        conn.commit()
        print(f"✅ Successfully executed {os.path.basename(filepath)}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error executing {os.path.basename(filepath)}: {e}")
        return False

def main():
    print("="*70)
    print("ChemLink Analytics Database - Schema Initialization")
    print("="*70)
    
    # Get schema directory
    schema_dir = Path(__file__).parent.parent / 'schema'
    
    # Schema files in order
    schema_files = [
        '01_create_schemas.sql',
        '02_staging_tables.sql',
        '03_core_tables.sql',
        '04_aggregate_views.sql',
        '05_ai_views.sql'
    ]
    
    # Connect to database
    print("\n📡 Connecting to analytics database...")
    try:
        conn = get_analytics_db_connection()
        print("✅ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return 1
    
    # Execute each schema file
    success_count = 0
    for filename in schema_files:
        filepath = schema_dir / filename
        if not filepath.exists():
            print(f"⚠️  File not found: {filename}")
            continue
        
        if execute_sql_file(conn, filepath):
            success_count += 1
    
    conn.close()
    
    # Summary
    print("\n" + "="*70)
    print("Schema Initialization Complete")
    print("="*70)
    print(f"✅ Success: {success_count}/{len(schema_files)} files")
    
    if success_count == len(schema_files):
        print("\n🎉 All schemas created successfully!")
        print("\nNext steps:")
        print("  1. View schemas in pgAdmin")
        print("  2. Run ETL pipeline: python scripts/etl_pipeline.py")
        return 0
    else:
        print(f"\n⚠️  {len(schema_files) - success_count} files failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Quick setup test script
Tests all database connections and verifies setup
"""

import os
from db_config import test_connections

def main():
    print("=" * 70)
    print("ChemLink Analytics Database - Setup Test")
    print("=" * 70)
    
    # Check .env file exists
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path):
        print("\n❌ ERROR: .env file not found!")
        print("   Copy .env.example to .env and configure your local postgres password")
        return
    
    print("\n✅ .env file found")
    
    # Test all connections
    print("\n" + "=" * 70)
    print("Testing Database Connections...")
    print("=" * 70)
    
    results = test_connections()
    
    all_ok = True
    for db_name, result in results.items():
        print(f"\n{db_name}:")
        if result['status'] == 'OK':
            print(f"  ✅ Connected successfully")
            if 'users' in result:
                print(f"  └─ Active users: {result['users']:,}")
            if 'version' in result:
                print(f"  └─ {result['version']}")
        else:
            all_ok = False
            print(f"  ❌ Connection failed")
            print(f"  └─ Error: {result['error']}")
    
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ All connections successful! Ready to proceed.")
        print("\nNext steps:")
        print("  1. Initialize schema: python scripts/init_schema.py")
        print("  2. Run ETL pipeline: python scripts/etl_pipeline.py")
    else:
        print("⚠️  Some connections failed. Please fix issues above.")
        if results['analytics_db']['status'] == 'ERROR':
            print("\nTo create the analytics database:")
            print("  psql -U postgres")
            print("  CREATE DATABASE chemlink_analytics;")
            print("  \\q")
            print("\nThen update ANALYTICS_DB_PASSWORD in .env file")
    print("=" * 70)

if __name__ == '__main__':
    main()

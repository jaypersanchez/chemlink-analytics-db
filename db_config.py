import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# SOURCE DATABASE CONNECTIONS (Production - READ-ONLY)
# ==============================================================================

def get_chemlink_source_connection():
    """Get connection to ChemLink Production database (READ-ONLY)"""
    return psycopg2.connect(
        host=os.getenv('CHEMLINK_PRD_DB_HOST'),
        port=os.getenv('CHEMLINK_PRD_DB_PORT', 5432),
        database=os.getenv('CHEMLINK_PRD_DB_NAME'),
        user=os.getenv('CHEMLINK_PRD_DB_USER'),
        password=os.getenv('CHEMLINK_PRD_DB_PASSWORD')
    )

def get_engagement_source_connection():
    """Get connection to Engagement Platform Production database (READ-ONLY)"""
    return psycopg2.connect(
        host=os.getenv('ENGAGEMENT_PRD_DB_HOST'),
        port=os.getenv('ENGAGEMENT_PRD_DB_PORT', 5432),
        database=os.getenv('ENGAGEMENT_PRD_DB_NAME'),
        user=os.getenv('ENGAGEMENT_PRD_DB_USER'),
        password=os.getenv('ENGAGEMENT_PRD_DB_PASSWORD')
    )

# ==============================================================================
# ANALYTICS DATABASE CONNECTION (Local)
# ==============================================================================

def get_analytics_db_connection():
    """Get connection to local Analytics database"""
    return psycopg2.connect(
        host=os.getenv('ANALYTICS_DB_HOST', 'localhost'),
        port=os.getenv('ANALYTICS_DB_PORT', 5432),
        database=os.getenv('ANALYTICS_DB_NAME'),
        user=os.getenv('ANALYTICS_DB_USER'),
        password=os.getenv('ANALYTICS_DB_PASSWORD')
    )

# ==============================================================================
# QUERY EXECUTION HELPERS
# ==============================================================================

def execute_query(connection, query, params=None):
    """Execute a query and return results as list of dictionaries"""
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        print(f"Database error: {e}")
        raise
    finally:
        connection.close()

def execute_write(connection, query, params=None):
    """Execute a write query (INSERT/UPDATE/DELETE) and commit"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            connection.commit()
            return cursor.rowcount
    except Exception as e:
        connection.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        connection.close()

def execute_many(connection, query, data_list):
    """Execute batch insert/update with list of tuples"""
    try:
        with connection.cursor() as cursor:
            cursor.executemany(query, data_list)
            connection.commit()
            return cursor.rowcount
    except Exception as e:
        connection.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        connection.close()

# ==============================================================================
# CONNECTION TESTING
# ==============================================================================

def test_connections():
    """Test all database connections"""
    results = {}
    
    # Test ChemLink source
    try:
        conn = get_chemlink_source_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM persons WHERE deleted_at IS NULL")
            count = cursor.fetchone()[0]
        conn.close()
        results['chemlink_source'] = {'status': 'OK', 'users': count}
    except Exception as e:
        results['chemlink_source'] = {'status': 'ERROR', 'error': str(e)}
    
    # Test Engagement source
    try:
        conn = get_engagement_source_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM persons WHERE deleted_at IS NULL")
            count = cursor.fetchone()[0]
        conn.close()
        results['engagement_source'] = {'status': 'OK', 'users': count}
    except Exception as e:
        results['engagement_source'] = {'status': 'ERROR', 'error': str(e)}
    
    # Test Analytics database
    try:
        conn = get_analytics_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
        conn.close()
        results['analytics_db'] = {'status': 'OK', 'version': version}
    except Exception as e:
        results['analytics_db'] = {'status': 'ERROR', 'error': str(e)}
    
    return results

if __name__ == '__main__':
    print("Testing database connections...")
    results = test_connections()
    
    for db_name, result in results.items():
        print(f"\n{db_name}:")
        if result['status'] == 'OK':
            print(f"  ✅ Connected successfully")
            if 'users' in result:
                print(f"  Users: {result['users']}")
            if 'version' in result:
                print(f"  Version: {result['version']}")
        else:
            print(f"  ❌ Connection failed: {result['error']}")

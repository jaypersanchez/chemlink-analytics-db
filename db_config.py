import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
DATA_ENV = os.getenv('DATA_ENV', 'local').lower()

def _build_connection(prefix, fallback_prefix=None, default_host='localhost', default_port=5432):
    """Create connection params from env vars with optional fallback"""
    host = os.getenv(f'{prefix}_HOST') or (fallback_prefix and os.getenv(f'{fallback_prefix}_HOST')) or default_host
    port = os.getenv(f'{prefix}_PORT') or (fallback_prefix and os.getenv(f'{fallback_prefix}_PORT')) or default_port
    database = os.getenv(f'{prefix}_NAME') or (fallback_prefix and os.getenv(f'{fallback_prefix}_NAME'))
    user = os.getenv(f'{prefix}_USER') or (fallback_prefix and os.getenv(f'{fallback_prefix}_USER'))
    password = os.getenv(f'{prefix}_PASSWORD') or (fallback_prefix and os.getenv(f'{fallback_prefix}_PASSWORD'))
    
    if not database or not user or not password:
        raise ValueError(f"Missing database credentials for prefix '{prefix}' (DATA_ENV={DATA_ENV})")
    
    return psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )

# ==============================================================================
# SOURCE DATABASE CONNECTIONS (Production - READ-ONLY)
# ==============================================================================

def get_chemlink_source_connection():
    """Get connection to ChemLink source database"""
    if DATA_ENV == 'kube':
        return _build_connection('CHEMLINK_DEV_DB', 'CHEMLINK_PRD_DB')
    return _build_connection('CHEMLINK_PRD_DB')

def get_engagement_source_connection():
    """Get connection to Engagement Platform source database"""
    if DATA_ENV == 'kube':
        return _build_connection('ENGAGEMENT_DEV_DB', 'ENGAGEMENT_PRD_DB')
    return _build_connection('ENGAGEMENT_PRD_DB')

# ==============================================================================
# ANALYTICS DATABASE CONNECTION (Local)
# ==============================================================================

def get_analytics_db_connection():
    """Get connection to analytics database"""
    if DATA_ENV == 'kube':
        return _build_connection('ANALYTICS_DEV_DB', 'ANALYTICS_DB')
    return _build_connection('ANALYTICS_DB')

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

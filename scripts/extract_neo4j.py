#!/usr/bin/env python3
"""
ETL Extract Script - Neo4j Graph Database
Extracts all nodes and relationships from Neo4j Aura PROD
Loads into staging.neo4j_* tables

Strategy: Full refresh (TRUNCATE + INSERT)
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from db_config import get_analytics_db_connection

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://b4e5eaae.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "D-6P6823dX1z7mmoBvT_kVTY1RHRrErBX9KG_x5yV74")

# Global stats
stats = {
    'start_time': None,
    'nodes_extracted': 0,
    'relationships_extracted': 0,
    'tables_loaded': 0,
    'errors': []
}

def log(message, level='INFO'):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {'INFO': '📝', 'SUCCESS': '✅', 'ERROR': '❌', 'WARNING': '⚠️', 'PROGRESS': '📊'}
    icon = icons.get(level, '📝')
    print(f"[{timestamp}] {icon} {message}")
    sys.stdout.flush()

def extract_from_neo4j(query, description):
    """Execute Cypher query and return results"""
    log(f"📥 Extracting {description}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run(query)
            records = [dict(record) for record in result]
            log(f"   ✅ Extracted {len(records):,} records", 'SUCCESS')
            driver.close()
            return records
    except Exception as e:
        log(f"   ❌ Error: {str(e)}", 'ERROR')
        stats['errors'].append({'query': description, 'error': str(e)})
        return []

def load_to_staging(analytics_conn, table_name, columns, rows):
    """Load data into staging table"""
    if not rows:
        log(f"⚠️  No data to load for {table_name}", 'WARNING')
        return 0
    
    log(f"Loading {len(rows):,} rows to staging.{table_name}...")
    start = time.time()
    
    try:
        # Truncate table
        with analytics_conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE staging.{table_name} CASCADE")
        analytics_conn.commit()
        
        # Build insert query
        placeholders = ','.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO staging.{table_name} ({','.join(columns)}) VALUES ({placeholders})"
        
        # Batch insert
        batch_size = 1000
        total_inserted = 0
        
        with analytics_conn.cursor() as cursor:
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                cursor.executemany(insert_query, batch)
                analytics_conn.commit()
                total_inserted += len(batch)
                
                if len(rows) > 1000:
                    progress = (total_inserted / len(rows)) * 100
                    log(f"  Progress: {total_inserted:,}/{len(rows):,} ({progress:.1f}%)", 'PROGRESS')
        
        elapsed = time.time() - start
        log(f"✅ Loaded {total_inserted:,} rows in {elapsed:.2f}s", 'SUCCESS')
        stats['tables_loaded'] += 1
        return total_inserted
        
    except Exception as e:
        analytics_conn.rollback()
        error_msg = f"Error loading {table_name}: {str(e)}"
        log(error_msg, 'ERROR')
        stats['errors'].append({'table': table_name, 'error': str(e)})
        return 0

def extract_person_nodes(analytics_conn):
    """Extract Person nodes"""
    query = """
    MATCH (p:Person)
    RETURN 
        p.person_id as person_id,
        p.email as email,
        p.secondary_email as secondary_email,
        p.first_name as first_name,
        p.last_name as last_name,
        p.mobile_number as mobile_number,
        p.mobile_number_country_code as mobile_number_country_code
    """
    records = extract_from_neo4j(query, "Person nodes")
    if records:
        columns = ['person_id', 'email', 'secondary_email', 'first_name', 'last_name', 
                   'mobile_number', 'mobile_number_country_code']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_persons', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_company_nodes(analytics_conn):
    """Extract Company nodes"""
    query = """
    MATCH (c:Company)
    RETURN 
        c.company_id as company_id,
        c.company_name as company_name
    """
    records = extract_from_neo4j(query, "Company nodes")
    if records:
        columns = ['company_id', 'company_name']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_companies', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_role_nodes(analytics_conn):
    """Extract Role nodes"""
    query = """
    MATCH (r:Role)
    RETURN 
        r.role_id as role_id,
        r.title as title
    """
    records = extract_from_neo4j(query, "Role nodes")
    if records:
        columns = ['role_id', 'title']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_roles', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_school_nodes(analytics_conn):
    """Extract School nodes"""
    query = """
    MATCH (s:School)
    RETURN 
        s.school_id as school_id,
        s.school_name as school_name
    """
    records = extract_from_neo4j(query, "School nodes")
    if records:
        columns = ['school_id', 'school_name']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_schools', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_degree_nodes(analytics_conn):
    """Extract Degree nodes"""
    query = """
    MATCH (d:Degree)
    RETURN 
        d.degree_id as degree_id,
        d.degree_name as degree_name
    """
    records = extract_from_neo4j(query, "Degree nodes")
    if records:
        columns = ['degree_id', 'degree_name']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_degrees', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_location_nodes(analytics_conn):
    """Extract Location nodes"""
    query = """
    MATCH (l:Location)
    RETURN 
        l.location_id as location_id,
        l.country as country
    """
    records = extract_from_neo4j(query, "Location nodes")
    if records:
        columns = ['location_id', 'country']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_locations', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_project_nodes(analytics_conn):
    """Extract Project nodes"""
    query = """
    MATCH (p:Project)
    RETURN 
        p.project_id as project_id,
        p.project_name as project_name
    """
    records = extract_from_neo4j(query, "Project nodes")
    if records:
        columns = ['project_id', 'project_name']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_projects', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_language_nodes(analytics_conn):
    """Extract Language nodes"""
    query = """
    MATCH (l:Language)
    RETURN 
        l.language_id as language_id,
        l.language_name as language_name
    """
    records = extract_from_neo4j(query, "Language nodes")
    if records:
        columns = ['language_id', 'language_name']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_languages', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_experience_nodes(analytics_conn):
    """Extract Experience nodes"""
    query = """
    MATCH (e:Experience)
    RETURN 
        e.experience_id as experience_id,
        date(e.start_date) as start_date,
        date(e.end_date) as end_date,
        e.type as type
    """
    records = extract_from_neo4j(query, "Experience nodes")
    if records:
        columns = ['experience_id', 'start_date', 'end_date', 'type']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_experiences', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_education_nodes(analytics_conn):
    """Extract Education nodes"""
    query = """
    MATCH (e:Education)
    RETURN 
        e.education_id as education_id,
        date(e.start_date) as start_date,
        date(e.end_date) as end_date,
        e.field_of_study as field_of_study
    """
    records = extract_from_neo4j(query, "Education nodes")
    if records:
        columns = ['education_id', 'start_date', 'end_date', 'field_of_study']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_educations', columns, rows)
        stats['nodes_extracted'] += len(rows)

def extract_relationships(analytics_conn):
    """Extract all relationships as edge list"""
    query = """
    MATCH (a)-[r]->(b)
    RETURN 
        CASE 
            WHEN a.person_id IS NOT NULL THEN a.person_id
            WHEN a.company_id IS NOT NULL THEN a.company_id
            WHEN a.role_id IS NOT NULL THEN a.role_id
            WHEN a.school_id IS NOT NULL THEN a.school_id
            WHEN a.degree_id IS NOT NULL THEN a.degree_id
            WHEN a.location_id IS NOT NULL THEN a.location_id
            WHEN a.project_id IS NOT NULL THEN a.project_id
            WHEN a.language_id IS NOT NULL THEN a.language_id
            WHEN a.experience_id IS NOT NULL THEN a.experience_id
            WHEN a.education_id IS NOT NULL THEN a.education_id
            ELSE toString(id(a))
        END as source_node_id,
        labels(a)[0] as source_node_type,
        type(r) as relationship_type,
        CASE 
            WHEN b.person_id IS NOT NULL THEN b.person_id
            WHEN b.company_id IS NOT NULL THEN b.company_id
            WHEN b.role_id IS NOT NULL THEN b.role_id
            WHEN b.school_id IS NOT NULL THEN b.school_id
            WHEN b.degree_id IS NOT NULL THEN b.degree_id
            WHEN b.location_id IS NOT NULL THEN b.location_id
            WHEN b.project_id IS NOT NULL THEN b.project_id
            WHEN b.language_id IS NOT NULL THEN b.language_id
            WHEN b.experience_id IS NOT NULL THEN b.experience_id
            WHEN b.education_id IS NOT NULL THEN b.education_id
            ELSE toString(id(b))
        END as target_node_id,
        labels(b)[0] as target_node_type
    """
    records = extract_from_neo4j(query, "All relationships")
    if records:
        columns = ['source_node_id', 'source_node_type', 'relationship_type', 
                   'target_node_id', 'target_node_type']
        rows = [[r.get(c) for c in columns] for r in records]
        load_to_staging(analytics_conn, 'neo4j_relationships', columns, rows)
        stats['relationships_extracted'] += len(rows)

def log_extraction(analytics_conn, status, error_message=None):
    """Log extraction run to metadata table"""
    try:
        with analytics_conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO meta.neo4j_extraction_log 
                (extraction_type, nodes_extracted, relationships_extracted, 
                 started_at, completed_at, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                'full',
                stats['nodes_extracted'],
                stats['relationships_extracted'],
                datetime.fromtimestamp(stats['start_time']),
                datetime.now(),
                status,
                error_message
            ))
        analytics_conn.commit()
    except Exception as e:
        log(f"Warning: Could not log extraction: {str(e)}", 'WARNING')

def print_summary():
    """Print extraction summary"""
    elapsed = time.time() - stats['start_time']
    
    log("\n" + "=" * 70)
    log("EXTRACTION SUMMARY")
    log("=" * 70)
    
    log(f"\n⏱️  Total Time: {elapsed:.2f}s ({elapsed/60:.2f} minutes)")
    log(f"📊 Nodes Extracted: {stats['nodes_extracted']:,}")
    log(f"🔗 Relationships Extracted: {stats['relationships_extracted']:,}")
    log(f"📋 Tables Loaded: {stats['tables_loaded']}")
    
    if stats['errors']:
        log(f"\n❌ Errors: {len(stats['errors'])}", 'ERROR')
        for error in stats['errors']:
            log(f"  • {error}", 'ERROR')
    else:
        log(f"\n✅ No Errors - Clean Extraction!", 'SUCCESS')
    
    log("\n" + "=" * 70)

def main():
    stats['start_time'] = time.time()
    
    log("=" * 70)
    log("ETL EXTRACT - Neo4j Graph Database")
    log("=" * 70)
    log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Neo4j URI: {NEO4J_URI}")
    log(f"Strategy: FULL REFRESH (TRUNCATE + INSERT)")
    
    # Connect to analytics database
    log("\n📡 Connecting to analytics database...")
    try:
        analytics_conn = get_analytics_db_connection()
        log("Connected successfully", 'SUCCESS')
    except Exception as e:
        log(f"Failed to connect: {str(e)}", 'ERROR')
        return 1
    
    try:
        # Extract all node types
        log("\n" + "=" * 70)
        log("EXTRACTING NODE DATA")
        log("=" * 70)
        
        extract_person_nodes(analytics_conn)
        extract_company_nodes(analytics_conn)
        extract_role_nodes(analytics_conn)
        extract_school_nodes(analytics_conn)
        extract_degree_nodes(analytics_conn)
        extract_location_nodes(analytics_conn)
        extract_project_nodes(analytics_conn)
        extract_language_nodes(analytics_conn)
        extract_experience_nodes(analytics_conn)
        extract_education_nodes(analytics_conn)
        
        # Extract relationships
        log("\n" + "=" * 70)
        log("EXTRACTING RELATIONSHIP DATA")
        log("=" * 70)
        
        extract_relationships(analytics_conn)
        
        # Log success
        log_extraction(analytics_conn, 'success')
        
        # Print summary
        print_summary()
        
        log("\n✅ NEO4J EXTRACTION COMPLETE", 'SUCCESS')
        log("\nNext steps:")
        log("  1. Run transform: python scripts/transform.py")
        log("  2. Run aggregate: python scripts/aggregate.py")
        
        return 0
        
    except KeyboardInterrupt:
        log("\n⚠️  Extraction cancelled by user", 'WARNING')
        log_extraction(analytics_conn, 'cancelled', 'User interrupted')
        print_summary()
        return 130
        
    except Exception as e:
        log(f"\n❌ Unexpected error: {str(e)}", 'ERROR')
        log(traceback.format_exc(), 'ERROR')
        log_extraction(analytics_conn, 'failed', str(e))
        print_summary()
        return 1
        
    finally:
        analytics_conn.close()

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
ETL Extract Script - Pull data from production databases
Only extracts records with valid person relationships (no orphans)

Strategy:
- Full refresh: TRUNCATE staging tables and reload all data
- Incremental: Only extract records updated since last run (future)
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

from db_config import (
    get_chemlink_source_connection,
    get_engagement_source_connection,
    get_analytics_db_connection
)

# Global stats
stats = {
    'start_time': None,
    'tables_extracted': 0,
    'total_rows_extracted': 0,
    'total_rows_loaded': 0,
    'errors': []
}

def log(message, level='INFO'):
    """Print timestamped log message with level"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {'INFO': '📝', 'SUCCESS': '✅', 'ERROR': '❌', 'WARNING': '⚠️', 'PROGRESS': '📊'}
    icon = icons.get(level, '📝')
    print(f"[{timestamp}] {icon} {message}")
    sys.stdout.flush()  # Ensure immediate output

def extract_table(source_conn, table_name, query, description):
    """Extract data from source table"""
    log(f"📥 Extracting {description}...")
    
    try:
        with source_conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            log(f"   ✅ Extracted {len(rows):,} rows from {table_name}")
            return rows, columns
    except Exception as e:
        log(f"   ❌ Error extracting {table_name}: {e}")
        return None, None

def load_to_staging(analytics_conn, schema, table_name, columns, rows):
    """Load data into staging table using TRUNCATE + INSERT strategy"""
    if not rows:
        log(f"Skipping {schema}.{table_name} (no data to load)", 'WARNING')
        return 0
    
    log(f"Loading {len(rows):,} rows to {schema}.{table_name}...", 'INFO')
    start = time.time()
    
    # Step 1: Clear existing data (TRUNCATE for full refresh)
    try:
        log(f"  Truncating {schema}.{table_name}...", 'INFO')
        with analytics_conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {schema}.{table_name} CASCADE")
        analytics_conn.commit()
        log(f"  Table truncated", 'SUCCESS')
    except Exception as e:
        error_msg = f"Warning: Could not truncate {schema}.{table_name}: {str(e)}"
        log(error_msg, 'WARNING')
        stats['errors'].append({'table': f"{schema}.{table_name}", 'error': error_msg})
        analytics_conn.rollback()
    
    # Step 2: Build insert query
    placeholders = ','.join(['%s'] * len(columns))
    insert_query = f"""
        INSERT INTO {schema}.{table_name} ({','.join(columns)})
        VALUES ({placeholders})
    """
    
    # Step 3: Batch insert with progress tracking
    # Smaller batches = more progress logs + less transaction time
    batch_size = 500 if len(rows) > 1000 else 200
    total_inserted = 0
    
    try:
        with analytics_conn.cursor() as cursor:
            num_batches = (len(rows) + batch_size - 1) // batch_size
            log(f"  Inserting in {num_batches} batches of {batch_size} rows...", 'INFO')
            
            last_status = time.time()
            for i in range(0, len(rows), batch_size):
                batch_num = (i // batch_size) + 1
                batch = rows[i:i + batch_size]
                
                batch_start = time.time()
                cursor.executemany(insert_query, batch)
                analytics_conn.commit()
                batch_time = time.time() - batch_start
                
                total_inserted += len(batch)
                progress_pct = (total_inserted / len(rows)) * 100
                log(f"  Batch {batch_num}/{num_batches}: {total_inserted:,}/{len(rows):,} rows ({progress_pct:.1f}%) - {batch_time:.2f}s", 'PROGRESS')
                
                # Emit heartbeat log every ~5 seconds even if batches are large
                if time.time() - last_status >= 5:
                    elapsed = time.time() - start
                    log(f"  ⏳ Still loading {schema}.{table_name}... {total_inserted:,}/{len(rows):,} rows ({progress_pct:.1f}%) after {elapsed:.1f}s", 'INFO')
                    last_status = time.time()
        
        elapsed = time.time() - start
        log(f"Successfully loaded {total_inserted:,} rows to {schema}.{table_name} in {elapsed:.2f}s", 'SUCCESS')
        stats['total_rows_loaded'] += total_inserted
        stats['tables_extracted'] += 1
        return total_inserted
        
    except Exception as e:
        analytics_conn.rollback()
        elapsed = time.time() - start
        error_msg = f"Error loading to {schema}.{table_name} after {elapsed:.2f}s: {str(e)}"
        log(error_msg, 'ERROR')
        log(f"  Failed at row {total_inserted}/{len(rows)}", 'ERROR')
        log(f"  Traceback:\n{traceback.format_exc()}", 'ERROR')
        stats['errors'].append({'table': f"{schema}.{table_name}", 'error': str(e), 'traceback': traceback.format_exc()})
        return 0

def extract_chemlink_data(analytics_conn):
    """Extract all ChemLink Service data"""
    log("\n" + "="*70)
    log("EXTRACTING CHEMLINK SERVICE DATA")
    log("="*70)
    
    source_conn = get_chemlink_source_connection()
    
    # Step 1: Extract persons first (need valid person IDs)
    query = """
        SELECT 
            id, person_id, name, profile, chemlink_id, kratos_id, hydra_id,
            first_name, middle_name, last_name, email, secondary_email,
            mobile_number, mobile_number_country_code,
            headline_description, linked_in_url, career_goals,
            business_experience_summary, profile_picture,
            location_id, company_id, role_id, has_finder,
            created_at, updated_at, deleted_at
        FROM persons
        WHERE deleted_at IS NULL
        ORDER BY id
    """
    rows, columns = extract_table(source_conn, 'persons', query, 'ChemLink persons')
    if rows:
        # Convert JSON profile column to string
        fixed_rows = []
        for row in rows:
            row_list = list(row)
            if row_list[3] is not None:  # profile column (4th column, index 3)
                row_list[3] = json.dumps(row_list[3])
            fixed_rows.append(tuple(row_list))
        load_to_staging(analytics_conn, 'staging', 'chemlink_persons', columns, fixed_rows)
        
        # Build valid person ID set
        valid_person_ids = tuple([row[0] for row in rows])  # id is first column
        log(f"   📋 Valid person IDs: {len(valid_person_ids):,}")
    else:
        log("   ❌ No persons found, skipping related tables")
        source_conn.close()
        return
    
    # Step 2: Extract experiences (only for valid persons)
    query = f"""
        SELECT 
            id, person_id, company_id, role_id, project_id, location_id,
            description, start_date, end_date, type,
            created_at, updated_at, deleted_at
        FROM experiences
        WHERE deleted_at IS NULL
          AND person_id IN %s
        ORDER BY person_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} experiences")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'chemlink_experiences', columns, rows)
    
    # Step 3: Extract education (only for valid persons)
    query = f"""
        SELECT 
            id, person_id, school_id, degree_id, field_of_study,
            description, start_date, end_date,
            created_at, updated_at, deleted_at
        FROM education
        WHERE deleted_at IS NULL
          AND person_id IN %s
        ORDER BY person_id, start_date DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} education records")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'chemlink_education', columns, rows)
    
    # Step 4: Extract collections (only for valid persons)
    query = f"""
        SELECT 
            id, person_id, name, description, privacy,
            created_at, updated_at, deleted_at
        FROM collections
        WHERE deleted_at IS NULL
          AND person_id IN %s
        ORDER BY person_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} collections")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'chemlink_collections', columns, rows)
    
    # Step 5: Extract query_votes (uses voter_id)
    query = f"""
        SELECT 
            id, type, profile_id, voter_id, score, search_key, 
            actual_query, remarks, created_at, updated_at, deleted_at
        FROM query_votes
        WHERE deleted_at IS NULL
          AND voter_id IN %s
        ORDER BY voter_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} query votes")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'chemlink_query_votes', columns, rows)
    
    # Step 6: Extract view_access (only for valid persons)
    query = f"""
        SELECT 
            id, person_id, type, expiry, metadata, 
            created_at, updated_at, deleted_at
        FROM view_access
        WHERE deleted_at IS NULL
          AND person_id IN %s
        ORDER BY person_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} view access records")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'chemlink_view_access', columns, rows)
    
    # Step 7: Extract glossary (no person filter; includes null descriptions)
    query = """
        SELECT 
            id, term, meaning, category, description,
            created_at, updated_at
        FROM glossary
        ORDER BY id
    """
    rows, columns = extract_table(source_conn, 'glossary', query, 'ChemLink glossary terms')
    if rows:
        load_to_staging(analytics_conn, 'staging', 'chemlink_glossary', columns, rows)
    
    source_conn.close()
    log("✅ ChemLink extraction complete")

def extract_engagement_data(analytics_conn):
    """Extract all Engagement Platform data"""
    log("\n" + "="*70)
    log("EXTRACTING ENGAGEMENT PLATFORM DATA")
    log("="*70)
    
    source_conn = get_engagement_source_connection()
    
    # Step 1: Extract persons first
    query = """
        SELECT 
            id, external_id, iam_id, email, first_name, last_name,
            company_name, role_title, employment_status,
            mobile_number, mobile_number_country_code,
            profile_picture_key, profile_pic_updated_at,
            created_at, updated_at, deleted_at
        FROM persons
        WHERE deleted_at IS NULL
        ORDER BY id
    """
    rows, columns = extract_table(source_conn, 'persons', query, 'Engagement persons')
    if rows:
        load_to_staging(analytics_conn, 'staging', 'engagement_persons', columns, rows)
        
        # Build valid person ID set
        valid_person_ids = tuple([row[0] for row in rows])  # id is first column
        log(f"   📋 Valid person IDs: {len(valid_person_ids):,}")
    else:
        log("   ❌ No persons found, skipping related tables")
        source_conn.close()
        return
    
    # Step 2: Extract posts (only for valid persons)
    query = f"""
        SELECT 
            id, person_id, type, content, link_url, media_keys,
            status, group_id, created_at, updated_at, deleted_at
        FROM posts
        WHERE deleted_at IS NULL
          AND person_id IN %s
        ORDER BY person_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} posts")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'engagement_posts', columns, rows)
    
    # Step 3: Extract comments (only for valid persons)
    query = f"""
        SELECT 
            id, post_id, person_id, content, parent_comment_id,
            created_at, updated_at, deleted_at
        FROM comments
        WHERE deleted_at IS NULL
          AND person_id IN %s
        ORDER BY person_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} comments")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'engagement_comments', columns, rows)
    
    # Step 4: Extract groups (only created by valid persons)
    query = f"""
        SELECT 
            id, name, description, created_by,
            created_at, updated_at, deleted_at
        FROM groups
        WHERE deleted_at IS NULL
          AND created_by IN %s
        ORDER BY created_by, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} groups")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'engagement_groups', columns, rows)
    
    # Step 5: Extract group_members (only for valid persons)
    query = f"""
        SELECT 
            id, group_id, person_id, role, confirmed_at,
            created_at, updated_at, deleted_at
        FROM group_members
        WHERE deleted_at IS NULL
          AND person_id IN %s
        ORDER BY person_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} group members")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'engagement_group_members', columns, rows)
    
    # Step 6: Extract mentions (only for valid persons)
    query = f"""
        SELECT 
            id, mentioned_person_id, post_id, comment_id,
            created_at, deleted_at
        FROM mentions
        WHERE deleted_at IS NULL
          AND mentioned_person_id IN %s
        ORDER BY mentioned_person_id, created_at DESC
    """
    with source_conn.cursor() as cursor:
        cursor.execute(query, (valid_person_ids,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        log(f"   ✅ Extracted {len(rows):,} mentions")
    
    if rows:
        load_to_staging(analytics_conn, 'staging', 'engagement_mentions', columns, rows)
    
    source_conn.close()
    log("✅ Engagement extraction complete")

def print_summary():
    """Print extraction summary statistics"""
    elapsed_total = time.time() - stats['start_time']
    
    log("\n" + "="*70, 'INFO')
    log("EXTRACTION SUMMARY", 'INFO')
    log("="*70, 'INFO')
    
    log(f"\n⏱️  Total Time: {elapsed_total:.2f}s ({elapsed_total/60:.2f} minutes)", 'INFO')
    log(f"📊 Tables Processed: {stats['tables_extracted']}", 'INFO')
    log(f"📥 Rows Extracted: {stats['total_rows_extracted']:,}", 'INFO')
    log(f"📤 Rows Loaded: {stats['total_rows_loaded']:,}", 'INFO')
    
    if stats['total_rows_extracted'] > 0:
        rows_per_sec = stats['total_rows_extracted'] / elapsed_total
        log(f"🚀 Throughput: {rows_per_sec:.0f} rows/second", 'INFO')
    
    if stats['errors']:
        log(f"\n❌ Errors Encountered: {len(stats['errors'])}", 'ERROR')
        for i, error in enumerate(stats['errors'], 1):
            log(f"  {i}. Table: {error.get('table', 'Unknown')}", 'ERROR')
            log(f"     Error: {error.get('error', 'Unknown')}", 'ERROR')
    else:
        log(f"\n✅ No Errors - Clean Extraction!", 'SUCCESS')
    
    log("\n" + "="*70, 'INFO')

def main():
    stats['start_time'] = time.time()
    
    log("="*70, 'INFO')
    log("ETL EXTRACT - Production to Staging", 'INFO')
    log("="*70, 'INFO')
    log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'INFO')
    log(f"Strategy: FULL REFRESH (TRUNCATE + INSERT)", 'INFO')
    log(f"Orphan Filtering: ENABLED (only records with valid person_id)", 'INFO')
    
    # Connect to analytics database
    log("\n📡 Connecting to analytics database...", 'INFO')
    try:
        analytics_conn = get_analytics_db_connection()
        log("Connected to analytics database successfully", 'SUCCESS')
    except Exception as e:
        log(f"Failed to connect to analytics database: {str(e)}", 'ERROR')
        log(f"Traceback:\n{traceback.format_exc()}", 'ERROR')
        return 1
    
    # Extract from both production databases
    try:
        extract_chemlink_data(analytics_conn)
        extract_engagement_data(analytics_conn)
    except KeyboardInterrupt:
        log("\n⚠️  Extraction cancelled by user (Ctrl+C)", 'WARNING')
        analytics_conn.close()
        print_summary()
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        log(f"Unexpected error during extraction: {str(e)}", 'ERROR')
        log(f"Traceback:\n{traceback.format_exc()}", 'ERROR')
        stats['errors'].append({'error': 'Unexpected error', 'details': str(e), 'traceback': traceback.format_exc()})
        analytics_conn.close()
        print_summary()
        return 1
    
    analytics_conn.close()
    
    # Print summary
    print_summary()
    
    # Determine exit status
    if stats['errors']:
        log("⚠️  Extraction completed with errors", 'WARNING')
        log("\nRecommendation: Review errors above before proceeding", 'WARNING')
        return 1
    else:
        log("✅ EXTRACTION COMPLETE - All data loaded successfully!", 'SUCCESS')
        log("\nNext steps:", 'INFO')
        log("  1. View data in pgAdmin (staging schema)", 'INFO')
        log("  2. Run transform: python scripts/transform.py", 'INFO')
        return 0

if __name__ == '__main__':
    sys.exit(main())

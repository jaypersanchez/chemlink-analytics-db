#!/usr/bin/env python3
"""
ETL Transform Script - Transform staging data into core unified tables

Transforms:
1. staging.chemlink_persons + staging.engagement_persons → core.unified_users
2. All activity tables → core.user_activity_events
3. Aggregate by cohort → core.user_cohorts
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

from db_config import get_analytics_db_connection

# Global stats
stats = {
    'start_time': None,
    'tables_transformed': 0,
    'total_rows_processed': 0,
    'total_rows_inserted': 0,
    'errors': []
}

def log(message, level='INFO'):
    """Print timestamped log message with level"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {'INFO': '📝', 'SUCCESS': '✅', 'ERROR': '❌', 'WARNING': '⚠️', 'PROGRESS': '📊'}
    icon = icons.get(level, '📝')
    print(f"[{timestamp}] {icon} {message}")
    sys.stdout.flush()

def execute_transform(conn, description, sql):
    """Execute a transformation SQL statement"""
    log(f"Transforming {description}...", 'INFO')
    start = time.time()
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows_affected = cursor.rowcount
        conn.commit()
        
        elapsed = time.time() - start
        log(f"  Transformed {rows_affected:,} rows in {elapsed:.2f}s", 'SUCCESS')
        stats['total_rows_inserted'] += rows_affected
        stats['tables_transformed'] += 1
        return rows_affected
        
    except Exception as e:
        conn.rollback()
        elapsed = time.time() - start
        error_msg = f"Error transforming {description} after {elapsed:.2f}s: {str(e)}"
        log(error_msg, 'ERROR')
        log(f"  Traceback:\n{traceback.format_exc()}", 'ERROR')
        stats['errors'].append({'step': description, 'error': str(e), 'traceback': traceback.format_exc()})
        return 0

def transform_unified_users(conn):
    """Transform staging persons data into core.unified_users"""
    log("\n" + "="*70, 'INFO')
    log("STEP 1: Creating Unified Users", 'INFO')
    log("="*70, 'INFO')
    
    # Truncate existing data
    log("  Clearing core.unified_users...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE core.unified_users CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    # Build unified users table
    transform_sql = """
    INSERT INTO core.unified_users (
        chemlink_id,
        engagement_person_id,
        person_id,
        email,
        first_name,
        last_name,
        has_finder,
        user_type,
        experience_count,
        education_count,
        profile_completion_score,
        posts_created,
        comments_made,
        votes_cast,
        collections_created,
        mentions_received,
        groups_joined,
        views_given,
        signup_date,
        last_activity_date,
        first_post_date,
        first_vote_date,
        days_since_signup,
        days_to_first_activity,
        user_lifecycle_stage,
        activation_status,
        activated_at,
        is_test_account,
        kratos_identity_id,
        kratos_identity_state,
        last_login_at,
        total_sessions,
        active_sessions,
        mfa_enabled,
        highest_aal,
        account_locked,
        credential_type,
        created_at,
        updated_at,
        deleted_at
    )
    SELECT DISTINCT ON (cp.id)
        -- Primary identifiers
        cp.id AS chemlink_id,
        ep.id AS engagement_person_id,
        cp.person_id AS person_id,
        
        -- Basic profile
        COALESCE(cp.email, ep.email) AS email,
        COALESCE(cp.first_name, ep.first_name) AS first_name,
        COALESCE(cp.last_name, ep.last_name) AS last_name,
        
        -- User type
        COALESCE(cp.has_finder, FALSE) AS has_finder,
        CASE WHEN cp.has_finder THEN 'FINDER' ELSE 'STANDARD' END AS user_type,
        
        -- Profile metrics (from ChemLink)
        (SELECT COUNT(*) FROM staging.chemlink_experiences e 
         WHERE e.person_id = cp.id AND e.deleted_at IS NULL) AS experience_count,
        (SELECT COUNT(*) FROM staging.chemlink_education ed 
         WHERE ed.person_id = cp.id AND ed.deleted_at IS NULL) AS education_count,
        
        -- Profile completion score (0-100)
        (
            CASE WHEN cp.first_name IS NOT NULL AND LENGTH(cp.first_name) > 0 THEN 10 ELSE 0 END +
            CASE WHEN cp.last_name IS NOT NULL AND LENGTH(cp.last_name) > 0 THEN 10 ELSE 0 END +
            CASE WHEN cp.email IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN cp.headline_description IS NOT NULL AND LENGTH(cp.headline_description) > 10 THEN 15 ELSE 0 END +
            CASE WHEN cp.linked_in_url IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN (SELECT COUNT(*) FROM staging.chemlink_experiences e WHERE e.person_id = cp.id AND e.deleted_at IS NULL) > 0 THEN 20 ELSE 0 END +
            CASE WHEN (SELECT COUNT(*) FROM staging.chemlink_education ed WHERE ed.person_id = cp.id AND ed.deleted_at IS NULL) > 0 THEN 15 ELSE 0 END +
            CASE WHEN cp.location_id IS NOT NULL THEN 10 ELSE 0 END
        ) AS profile_completion_score,
        
        -- Engagement metrics (from Engagement Platform)
        (SELECT COUNT(*) FROM staging.engagement_posts p 
         WHERE p.person_id = ep.id AND p.deleted_at IS NULL) AS posts_created,
        (SELECT COUNT(*) FROM staging.engagement_comments c 
         WHERE c.person_id = ep.id AND c.deleted_at IS NULL) AS comments_made,
        (SELECT COUNT(*) FROM staging.chemlink_query_votes qv 
         WHERE qv.voter_id = cp.id AND qv.deleted_at IS NULL) AS votes_cast,
        (SELECT COUNT(*) FROM staging.chemlink_collections col 
         WHERE col.person_id = cp.id AND col.deleted_at IS NULL) AS collections_created,
        (SELECT COUNT(*) FROM staging.engagement_mentions m 
         WHERE m.mentioned_person_id = ep.id AND m.deleted_at IS NULL) AS mentions_received,
        (SELECT COUNT(*) FROM staging.engagement_group_members gm 
         WHERE gm.person_id = ep.id AND gm.deleted_at IS NULL) AS groups_joined,
        (SELECT COUNT(*) FROM staging.chemlink_view_access va 
         WHERE va.person_id = cp.id AND va.deleted_at IS NULL) AS views_given,
        
        -- Calculated lifecycle fields
        cp.created_at AS signup_date,
        
        -- Last activity date (max of any activity)
        GREATEST(
            cp.updated_at,
            COALESCE((SELECT MAX(p.created_at) FROM staging.engagement_posts p WHERE p.person_id = ep.id), cp.created_at),
            COALESCE((SELECT MAX(c.created_at) FROM staging.engagement_comments c WHERE c.person_id = ep.id), cp.created_at),
            COALESCE((SELECT MAX(qv.created_at) FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id), cp.created_at),
            COALESCE((SELECT MAX(col.created_at) FROM staging.chemlink_collections col WHERE col.person_id = cp.id), cp.created_at)
        ) AS last_activity_date,
        
        -- First activity dates
        (SELECT MIN(p.created_at) FROM staging.engagement_posts p WHERE p.person_id = ep.id) AS first_post_date,
        (SELECT MIN(qv.created_at) FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id) AS first_vote_date,
        
        -- Days since signup
        EXTRACT(DAY FROM (CURRENT_TIMESTAMP - cp.created_at)) AS days_since_signup,
        
        -- Days to first activity (any activity)
        EXTRACT(DAY FROM (
            LEAST(
                COALESCE((SELECT MIN(p.created_at) FROM staging.engagement_posts p WHERE p.person_id = ep.id), '9999-12-31'::TIMESTAMP),
                COALESCE((SELECT MIN(c.created_at) FROM staging.engagement_comments c WHERE c.person_id = ep.id), '9999-12-31'::TIMESTAMP),
                COALESCE((SELECT MIN(qv.created_at) FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id), '9999-12-31'::TIMESTAMP),
                COALESCE((SELECT MIN(col.created_at) FROM staging.chemlink_collections col WHERE col.person_id = cp.id), '9999-12-31'::TIMESTAMP)
            ) - cp.created_at
        )) AS days_to_first_activity,
        
        -- User lifecycle stage
        CASE 
            WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - GREATEST(
                cp.updated_at,
                COALESCE((SELECT MAX(p.created_at) FROM staging.engagement_posts p WHERE p.person_id = ep.id), cp.created_at),
                COALESCE((SELECT MAX(qv.created_at) FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id), cp.created_at)
            ))) > 90 THEN 'CHURNED'
            WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - GREATEST(
                cp.updated_at,
                COALESCE((SELECT MAX(p.created_at) FROM staging.engagement_posts p WHERE p.person_id = ep.id), cp.created_at),
                COALESCE((SELECT MAX(qv.created_at) FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id), cp.created_at)
            ))) > 30 THEN 'DORMANT'
            WHEN EXISTS(SELECT 1 FROM staging.engagement_posts p WHERE p.person_id = ep.id) 
                OR EXISTS(SELECT 1 FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id)
                OR EXISTS(SELECT 1 FROM staging.chemlink_collections col WHERE col.person_id = cp.id) THEN 'ENGAGED'
            WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - cp.created_at)) <= 7 THEN 'NEW'
            ELSE 'ACTIVATED'
        END AS user_lifecycle_stage,
        
        -- Activation status
        CASE WHEN EXISTS(SELECT 1 FROM staging.engagement_posts p WHERE p.person_id = ep.id) 
                OR EXISTS(SELECT 1 FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id)
                OR EXISTS(SELECT 1 FROM staging.chemlink_collections col WHERE col.person_id = cp.id)
            THEN TRUE ELSE FALSE 
        END AS activation_status,
        
        -- Activated at (first activity timestamp)
        LEAST(
            COALESCE((SELECT MIN(p.created_at) FROM staging.engagement_posts p WHERE p.person_id = ep.id), '9999-12-31'::TIMESTAMP),
            COALESCE((SELECT MIN(c.created_at) FROM staging.engagement_comments c WHERE c.person_id = ep.id), '9999-12-31'::TIMESTAMP),
            COALESCE((SELECT MIN(qv.created_at) FROM staging.chemlink_query_votes qv WHERE qv.voter_id = cp.id), '9999-12-31'::TIMESTAMP),
            COALESCE((SELECT MIN(col.created_at) FROM staging.chemlink_collections col WHERE col.person_id = cp.id), '9999-12-31'::TIMESTAMP)
        ) AS activated_at,
        
        -- Data quality - mark test accounts
        CASE WHEN cp.email IN ('jsanchez@nmblr.ai', 'jaypersanchez@gmail.com', 'virlanchainworks@gmail.com')
            THEN TRUE ELSE FALSE 
        END AS is_test_account,
        
        -- Kratos authentication data
        ki.id AS kratos_identity_id,
        ki.state AS kratos_identity_state,
        (SELECT MAX(authenticated_at) FROM staging.kratos_sessions ks WHERE ks.identity_id = ki.id) AS last_login_at,
        (SELECT COUNT(*) FROM staging.kratos_sessions ks WHERE ks.identity_id = ki.id) AS total_sessions,
        (SELECT COUNT(*) FROM staging.kratos_sessions ks WHERE ks.identity_id = ki.id AND ks.active = TRUE) AS active_sessions,
        CASE WHEN kic.type = 'totp' OR kic.type = 'webauthn' THEN TRUE ELSE FALSE END AS mfa_enabled,
        (SELECT MAX(aal) FROM staging.kratos_sessions ks WHERE ks.identity_id = ki.id) AS highest_aal,
        COALESCE((ki.traits->>'properties')::jsonb->>'locked', 'false')::boolean AS account_locked,
        kic.type AS credential_type,
        
        -- Timestamps
        cp.created_at,
        cp.updated_at,
        cp.deleted_at
        
    FROM staging.chemlink_persons cp
    LEFT JOIN staging.engagement_persons ep ON cp.id = ep.external_id
    LEFT JOIN staging.kratos_identities ki ON cp.kratos_id::uuid = ki.id
    LEFT JOIN staging.kratos_identity_credentials kic ON ki.id = kic.identity_id
    WHERE cp.deleted_at IS NULL
    ORDER BY cp.id;
    """
    
    return execute_transform(conn, "core.unified_users", transform_sql)

def transform_glossary_terms(conn):
    """Transform staging glossary data into core.glossary_terms"""
    log("\n" + "="*70, 'INFO')
    log("STEP 1B: Publishing Glossary Terms", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing core.glossary_terms...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE core.glossary_terms")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    transform_sql = """
    INSERT INTO core.glossary_terms (
        glossary_id,
        term,
        meaning,
        category,
        description,
        display_value,
        created_at,
        updated_at
    )
    SELECT
        g.id AS glossary_id,
        NULLIF(TRIM(g.term), '') AS term,
        NULLIF(TRIM(g.meaning), '') AS meaning,
        NULLIF(TRIM(g.category), '') AS category,
        g.description,
        COALESCE(
            NULLIF(TRIM(g.term), ''),
            NULLIF(TRIM(g.meaning), ''),
            NULLIF(TRIM(g.category), '')
        ) AS display_value,
        g.created_at,
        g.updated_at
    FROM staging.chemlink_glossary g
    WHERE g.description IS NOT NULL
      AND TRIM(g.description) <> '';
    """
    
    return execute_transform(conn, "core.glossary_terms", transform_sql)

def transform_user_activity_events(conn):
    """Transform all activity tables into core.user_activity_events"""
    log("\n" + "="*70, 'INFO')
    log("STEP 2: Creating User Activity Events", 'INFO')
    log("="*70, 'INFO')
    
    # Truncate existing data
    log("  Clearing core.user_activity_events...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE core.user_activity_events CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    # Insert posts
    log("  Adding post events...", 'INFO')
    post_sql = """
    INSERT INTO core.user_activity_events (
        user_id, activity_type, activity_date,
        source_database, source_table, source_id,
        metadata, days_since_signup, is_first_activity_of_type
    )
    SELECT 
        u.chemlink_id AS user_id,
        'post' AS activity_type,
        p.created_at AS activity_date,
        'engagement' AS source_database,
        'posts' AS source_table,
        ('x' || SUBSTRING(REPLACE(p.id::TEXT, '-', ''), 1, 15))::BIT(60)::BIGINT AS source_id,
        json_build_object(
            'type', p.type,
            'status', p.status,
            'has_link', CASE WHEN p.link_url IS NOT NULL THEN true ELSE false END,
            'has_media', CASE WHEN p.media_keys IS NOT NULL THEN true ELSE false END
        )::JSONB AS metadata,
        EXTRACT(DAY FROM (p.created_at - u.signup_date)) AS days_since_signup,
        p.created_at = (SELECT MIN(p2.created_at) FROM staging.engagement_posts p2 WHERE p2.person_id = p.person_id) AS is_first_activity_of_type
    FROM staging.engagement_posts p
    JOIN staging.engagement_persons ep ON p.person_id = ep.id
    JOIN core.unified_users u ON ep.id = u.engagement_person_id
    WHERE p.deleted_at IS NULL;
    """
    execute_transform(conn, "post events", post_sql)
    
    # Insert comments
    log("  Adding comment events...", 'INFO')
    comment_sql = """
    INSERT INTO core.user_activity_events (
        user_id, activity_type, activity_date,
        source_database, source_table, source_id,
        metadata, days_since_signup, is_first_activity_of_type
    )
    SELECT 
        u.chemlink_id AS user_id,
        'comment' AS activity_type,
        c.created_at AS activity_date,
        'engagement' AS source_database,
        'comments' AS source_table,
        ('x' || SUBSTRING(REPLACE(c.id::TEXT, '-', ''), 1, 15))::BIT(60)::BIGINT AS source_id,
        json_build_object(
            'post_id', c.post_id::TEXT,
            'is_reply', CASE WHEN c.parent_comment_id IS NOT NULL THEN true ELSE false END
        )::JSONB AS metadata,
        EXTRACT(DAY FROM (c.created_at - u.signup_date)) AS days_since_signup,
        c.created_at = (SELECT MIN(c2.created_at) FROM staging.engagement_comments c2 WHERE c2.person_id = c.person_id) AS is_first_activity_of_type
    FROM staging.engagement_comments c
    JOIN staging.engagement_persons ep ON c.person_id = ep.id
    JOIN core.unified_users u ON ep.id = u.engagement_person_id
    WHERE c.deleted_at IS NULL;
    """
    execute_transform(conn, "comment events", comment_sql)
    
    # Insert votes
    log("  Adding vote events...", 'INFO')
    vote_sql = """
    INSERT INTO core.user_activity_events (
        user_id, activity_type, activity_date,
        source_database, source_table, source_id,
        metadata, days_since_signup, is_first_activity_of_type
    )
    SELECT 
        qv.voter_id AS user_id,
        'vote' AS activity_type,
        qv.created_at AS activity_date,
        'chemlink' AS source_database,
        'query_votes' AS source_table,
        qv.id AS source_id,
        json_build_object(
            'type', qv.type,
            'score', qv.score,
            'profile_id', qv.profile_id
        )::JSONB AS metadata,
        EXTRACT(DAY FROM (qv.created_at - u.signup_date)) AS days_since_signup,
        qv.created_at = (SELECT MIN(qv2.created_at) FROM staging.chemlink_query_votes qv2 WHERE qv2.voter_id = qv.voter_id) AS is_first_activity_of_type
    FROM staging.chemlink_query_votes qv
    JOIN core.unified_users u ON qv.voter_id = u.chemlink_id
    WHERE qv.deleted_at IS NULL;
    """
    execute_transform(conn, "vote events", vote_sql)
    
    # Insert collections
    log("  Adding collection events...", 'INFO')
    collection_sql = """
    INSERT INTO core.user_activity_events (
        user_id, activity_type, activity_date,
        source_database, source_table, source_id,
        metadata, days_since_signup, is_first_activity_of_type
    )
    SELECT 
        col.person_id AS user_id,
        'collection' AS activity_type,
        col.created_at AS activity_date,
        'chemlink' AS source_database,
        'collections' AS source_table,
        col.id AS source_id,
        json_build_object(
            'name', col.name,
            'privacy', col.privacy
        )::JSONB AS metadata,
        EXTRACT(DAY FROM (col.created_at - u.signup_date)) AS days_since_signup,
        col.created_at = (SELECT MIN(col2.created_at) FROM staging.chemlink_collections col2 WHERE col2.person_id = col.person_id) AS is_first_activity_of_type
    FROM staging.chemlink_collections col
    JOIN core.unified_users u ON col.person_id = u.chemlink_id
    WHERE col.deleted_at IS NULL;
    """
    execute_transform(conn, "collection events", collection_sql)
    
    # Insert profile views
    log("  Adding view events...", 'INFO')
    view_sql = """
    INSERT INTO core.user_activity_events (
        user_id, activity_type, activity_date,
        source_database, source_table, source_id,
        metadata, days_since_signup, is_first_activity_of_type
    )
    SELECT 
        va.person_id AS user_id,
        'view' AS activity_type,
        va.created_at AS activity_date,
        'chemlink' AS source_database,
        'view_access' AS source_table,
        va.id AS source_id,
        json_build_object(
            'type', va.type,
            'expiry', va.expiry
        )::JSONB AS metadata,
        EXTRACT(DAY FROM (va.created_at - u.signup_date)) AS days_since_signup,
        va.created_at = (SELECT MIN(va2.created_at) FROM staging.chemlink_view_access va2 WHERE va2.person_id = va.person_id) AS is_first_activity_of_type
    FROM staging.chemlink_view_access va
    JOIN core.unified_users u ON va.person_id = u.chemlink_id
    WHERE va.deleted_at IS NULL;
    """
    execute_transform(conn, "view events", view_sql)
    
    log("✅ All activity events transformed", 'SUCCESS')

def transform_user_cohorts(conn):
    """Calculate cohort metrics"""
    log("\n" + "="*70, 'INFO')
    log("STEP 3: Calculating User Cohorts", 'INFO')
    log("="*70, 'INFO')
    
    # Truncate existing data
    log("  Clearing core.user_cohorts...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE core.user_cohorts CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    cohort_sql = """
    INSERT INTO core.user_cohorts (
        cohort_month,
        total_users,
        finder_users,
        standard_users,
        avg_profile_completion,
        avg_experience_count,
        avg_education_count,
        activated_users,
        activation_rate,
        avg_days_to_activation,
        retained_30d,
        retained_60d,
        retained_90d,
        retention_rate_30d,
        retention_rate_60d,
        retention_rate_90d
    )
    SELECT 
        DATE_TRUNC('month', signup_date) AS cohort_month,
        COUNT(*) AS total_users,
        COUNT(*) FILTER (WHERE has_finder = TRUE) AS finder_users,
        COUNT(*) FILTER (WHERE has_finder = FALSE) AS standard_users,
        ROUND(AVG(profile_completion_score), 2) AS avg_profile_completion,
        ROUND(AVG(experience_count), 2) AS avg_experience_count,
        ROUND(AVG(education_count), 2) AS avg_education_count,
        COUNT(*) FILTER (WHERE activation_status = TRUE) AS activated_users,
        ROUND((COUNT(*) FILTER (WHERE activation_status = TRUE)::NUMERIC / COUNT(*)) * 100, 2) AS activation_rate,
        ROUND(AVG(days_to_first_activity) FILTER (WHERE days_to_first_activity IS NOT NULL AND days_to_first_activity < 10000), 2) AS avg_days_to_activation,
        COUNT(*) FILTER (WHERE last_activity_date >= signup_date + INTERVAL '30 days') AS retained_30d,
        COUNT(*) FILTER (WHERE last_activity_date >= signup_date + INTERVAL '60 days') AS retained_60d,
        COUNT(*) FILTER (WHERE last_activity_date >= signup_date + INTERVAL '90 days') AS retained_90d,
        ROUND((COUNT(*) FILTER (WHERE last_activity_date >= signup_date + INTERVAL '30 days')::NUMERIC / COUNT(*)) * 100, 2) AS retention_rate_30d,
        ROUND((COUNT(*) FILTER (WHERE last_activity_date >= signup_date + INTERVAL '60 days')::NUMERIC / COUNT(*)) * 100, 2) AS retention_rate_60d,
        ROUND((COUNT(*) FILTER (WHERE last_activity_date >= signup_date + INTERVAL '90 days')::NUMERIC / COUNT(*)) * 100, 2) AS retention_rate_90d
    FROM core.unified_users
    WHERE deleted_at IS NULL
        AND is_test_account = FALSE
    GROUP BY DATE_TRUNC('month', signup_date)
    ORDER BY cohort_month DESC;
    """
    
    return execute_transform(conn, "core.user_cohorts", cohort_sql)

def transform_neo4j_data(conn):
    """Transform Neo4j graph data into core tables"""
    log("\n" + "="*70, 'INFO')
    log("STEP 4: Transforming Neo4j Graph Data", 'INFO')
    log("="*70, 'INFO')

    required_tables = [
        ('core', 'user_relationships'),
        ('core', 'career_paths'),
        ('core', 'education_networks'),
        ('core', 'company_networks'),
        ('core', 'location_networks'),
        ('core', 'project_collaborations'),
        ('staging', 'neo4j_relationships'),
        ('staging', 'neo4j_persons'),
        ('staging', 'neo4j_companies'),
        ('staging', 'neo4j_roles'),
        ('staging', 'neo4j_schools'),
        ('staging', 'neo4j_degrees'),
        ('staging', 'neo4j_locations'),
        ('staging', 'neo4j_projects'),
        ('staging', 'neo4j_languages'),
        ('staging', 'neo4j_experiences'),
        ('staging', 'neo4j_educations')
    ]
    
    missing_tables = []
    with conn.cursor() as cursor:
        for schema, table in required_tables:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = %s
                      AND table_name = %s
                )
                """,
                (schema, table)
            )
            exists = cursor.fetchone()[0]
            if not exists:
                missing_tables.append(f"{schema}.{table}")
    
    if missing_tables:
        log("  ⚠️ Neo4j schema not initialized; skipping Step 4", 'WARNING')
        log(f"     Missing tables: {', '.join(missing_tables)}", 'WARNING')
        log("     Run schema/neo4j_integration.sql and scripts/extract_neo4j.py to enable this step.", 'INFO')
        return 0
    
    # Transform user relationships (worked together, studied together, etc.)
    log("  Building user-to-user relationships...", 'INFO')
    
    # Clear existing data
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE core.user_relationships CASCADE")
        cursor.execute("TRUNCATE TABLE core.career_paths CASCADE")
        cursor.execute("TRUNCATE TABLE core.education_networks CASCADE")
        cursor.execute("TRUNCATE TABLE core.company_networks CASCADE")
        cursor.execute("TRUNCATE TABLE core.location_networks CASCADE")
        cursor.execute("TRUNCATE TABLE core.project_collaborations CASCADE")
    conn.commit()
    
    # 1. Build user relationships - WORKED_TOGETHER
    worked_together_sql = """
    INSERT INTO core.user_relationships (
        user_id, related_user_id, relationship_type, 
        relationship_strength, connection_context, first_connected_at
    )
    SELECT DISTINCT
        u1.chemlink_id as user_id,
        u2.chemlink_id as related_user_id,
        'WORKED_TOGETHER' as relationship_type,
        COUNT(DISTINCT c.company_id) as relationship_strength,
        jsonb_build_object(
            'companies', array_agg(DISTINCT c.company_name),
            'roles', array_agg(DISTINCT r.title)
        ) as connection_context,
        MIN(
            CASE 
                WHEN e1.start_date ~ '^\d{4}-\d{2}-\d{2}$' THEN e1.start_date::timestamp
                WHEN e1.start_date ~ '^\d{1,2}-\d{4}$' THEN to_date(e1.start_date, 'FMMM-YYYY')::timestamp
                ELSE NULL
            END
        ) as first_connected_at
    FROM staging.neo4j_relationships rel1
    JOIN staging.neo4j_relationships rel2 ON rel1.target_node_id = rel2.target_node_id
        AND rel1.target_node_type = 'Company'
        AND rel2.target_node_type = 'Company'
        AND rel1.source_node_id < rel2.source_node_id  -- Avoid duplicates
    JOIN staging.neo4j_persons p1 ON rel1.source_node_id = p1.person_id
    JOIN staging.neo4j_persons p2 ON rel2.source_node_id = p2.person_id
    JOIN core.unified_users u1 ON p1.email = u1.email
    JOIN core.unified_users u2 ON p2.email = u2.email
    LEFT JOIN staging.neo4j_companies c ON rel1.target_node_id = c.company_id
    LEFT JOIN staging.neo4j_experiences e1 ON rel1.source_node_id = e1.experience_id
    LEFT JOIN staging.neo4j_relationships rel_role ON rel1.source_node_id = rel_role.source_node_id AND rel_role.relationship_type = 'WORKED_AS'
    LEFT JOIN staging.neo4j_roles r ON rel_role.target_node_id = r.role_id
    WHERE rel1.relationship_type IN ('EXPERIENCED_IN', 'WORKED_AT')
        AND u1.chemlink_id != u2.chemlink_id
    GROUP BY u1.chemlink_id, u2.chemlink_id
    HAVING COUNT(DISTINCT c.company_id) > 0
    """
    execute_transform(conn, "user relationships (worked together)", worked_together_sql)
    
    # 2. Build user relationships - STUDIED_TOGETHER
    studied_together_sql = """
    INSERT INTO core.user_relationships (
        user_id, related_user_id, relationship_type, 
        relationship_strength, connection_context, first_connected_at
    )
    SELECT DISTINCT
        u1.chemlink_id as user_id,
        u2.chemlink_id as related_user_id,
        'STUDIED_TOGETHER' as relationship_type,
        COUNT(DISTINCT s.school_id) as relationship_strength,
        jsonb_build_object(
            'schools', array_agg(DISTINCT s.school_name),
            'degrees', array_agg(DISTINCT d.degree_name)
        ) as connection_context,
        MIN(
            CASE 
                WHEN ed1.start_date ~ '^\d{4}-\d{2}-\d{2}$' THEN ed1.start_date::timestamp
                WHEN ed1.start_date ~ '^\d{1,2}-\d{4}$' THEN to_date(ed1.start_date, 'FMMM-YYYY')::timestamp
                ELSE NULL
            END
        ) as first_connected_at
    FROM staging.neo4j_relationships rel1
    JOIN staging.neo4j_relationships rel2 ON rel1.target_node_id = rel2.target_node_id
        AND rel1.target_node_type = 'School'
        AND rel2.target_node_type = 'School'
        AND rel1.source_node_id < rel2.source_node_id
    JOIN staging.neo4j_persons p1 ON rel1.source_node_id = p1.person_id
    JOIN staging.neo4j_persons p2 ON rel2.source_node_id = p2.person_id
    JOIN core.unified_users u1 ON p1.email = u1.email
    JOIN core.unified_users u2 ON p2.email = u2.email
    LEFT JOIN staging.neo4j_schools s ON rel1.target_node_id = s.school_id
    LEFT JOIN staging.neo4j_educations ed1 ON rel1.source_node_id = ed1.education_id
    LEFT JOIN staging.neo4j_relationships rel_deg ON rel1.source_node_id = rel_deg.source_node_id AND rel_deg.relationship_type = 'EARNED'
    LEFT JOIN staging.neo4j_degrees d ON rel_deg.target_node_id = d.degree_id
    WHERE rel1.relationship_type IN ('EDUCATED_IN', 'STUDIED_AT')
        AND u1.chemlink_id != u2.chemlink_id
    GROUP BY u1.chemlink_id, u2.chemlink_id
    HAVING COUNT(DISTINCT s.school_id) > 0
    """
    execute_transform(conn, "user relationships (studied together)", studied_together_sql)
    
    # 3. Build company networks
    company_networks_sql = """
    INSERT INTO core.company_networks (
        company_id, company_name, role_id, role_title, user_ids, user_count
    )
    SELECT 
        c.company_id,
        c.company_name,
        r.role_id,
        r.title as role_title,
        array_agg(DISTINCT u.chemlink_id) as user_ids,
        COUNT(DISTINCT u.chemlink_id) as user_count
    FROM staging.neo4j_companies c
    JOIN staging.neo4j_relationships rel_comp ON c.company_id = rel_comp.target_node_id 
        AND rel_comp.target_node_type = 'Company'
    JOIN staging.neo4j_persons p ON rel_comp.source_node_id = p.person_id
    JOIN core.unified_users u ON p.email = u.email
    LEFT JOIN staging.neo4j_relationships rel_role ON rel_comp.source_node_id = rel_role.source_node_id 
        AND rel_role.relationship_type = 'WORKED_AS'
    LEFT JOIN staging.neo4j_roles r ON rel_role.target_node_id = r.role_id
    WHERE rel_comp.relationship_type IN ('WORKS_AT', 'WORKED_AT')
    GROUP BY c.company_id, c.company_name, r.role_id, r.title
    """
    execute_transform(conn, "company networks", company_networks_sql)
    
    # 4. Build education networks
    education_networks_sql = """
    INSERT INTO core.education_networks (
        school_id, school_name, degree_id, degree_name, 
        user_ids, user_count, graduation_year_min, graduation_year_max
    )
    SELECT 
        s.school_id,
        s.school_name,
        d.degree_id,
        d.degree_name,
        array_agg(DISTINCT u.chemlink_id) as user_ids,
        COUNT(DISTINCT u.chemlink_id) as user_count,
        MIN(
            EXTRACT(YEAR FROM (
                CASE 
                    WHEN ed.end_date ~ '^\d{4}-\d{2}-\d{2}$' THEN ed.end_date::date
                    WHEN ed.end_date ~ '^\d{1,2}-\d{4}$' THEN to_date(ed.end_date, 'FMMM-YYYY')
                ELSE NULL
                END
            ))
        ) as graduation_year_min,
        MAX(
            EXTRACT(YEAR FROM (
                CASE 
                    WHEN ed.end_date ~ '^\d{4}-\d{2}-\d{2}$' THEN ed.end_date::date
                    WHEN ed.end_date ~ '^\d{1,2}-\d{4}$' THEN to_date(ed.end_date, 'FMMM-YYYY')
                ELSE NULL
                END
            ))
        ) as graduation_year_max
    FROM staging.neo4j_schools s
    JOIN staging.neo4j_relationships rel_school ON s.school_id = rel_school.target_node_id
        AND rel_school.target_node_type = 'School'
    JOIN staging.neo4j_educations ed ON rel_school.source_node_id = ed.education_id
    JOIN staging.neo4j_relationships rel_person ON ed.education_id = rel_person.target_node_id
        AND rel_person.relationship_type = 'EDUCATED_IN'
    JOIN staging.neo4j_persons p ON rel_person.source_node_id = p.person_id
    JOIN core.unified_users u ON p.email = u.email
    LEFT JOIN staging.neo4j_relationships rel_deg ON ed.education_id = rel_deg.source_node_id
        AND rel_deg.relationship_type = 'EARNED'
    LEFT JOIN staging.neo4j_degrees d ON rel_deg.target_node_id = d.degree_id
    WHERE rel_school.relationship_type = 'STUDIED_AT'
    GROUP BY s.school_id, s.school_name, d.degree_id, d.degree_name
    """
    execute_transform(conn, "education networks", education_networks_sql)
    
    # 5. Build location networks
    location_networks_sql = """
    INSERT INTO core.location_networks (
        location_id, country, user_ids, user_count
    )
    SELECT 
        l.location_id,
        l.country,
        array_agg(DISTINCT u.chemlink_id) as user_ids,
        COUNT(DISTINCT u.chemlink_id) as user_count
    FROM staging.neo4j_locations l
    JOIN staging.neo4j_relationships rel ON l.location_id = rel.target_node_id
        AND rel.target_node_type = 'Location'
    JOIN staging.neo4j_persons p ON rel.source_node_id = p.person_id
    JOIN core.unified_users u ON p.email = u.email
    WHERE rel.relationship_type = 'LIVES_AT'
    GROUP BY l.location_id, l.country
    """
    execute_transform(conn, "location networks", location_networks_sql)
    
    # 6. Build project collaborations
    project_collab_sql = """
    INSERT INTO core.project_collaborations (
        project_id, project_name, company_id, user_ids, user_count, role_ids
    )
    SELECT 
        proj.project_id,
        proj.project_name,
        c.company_id,
        array_agg(DISTINCT u.chemlink_id) as user_ids,
        COUNT(DISTINCT u.chemlink_id) as user_count,
        array_agg(DISTINCT r.title) as role_ids
    FROM staging.neo4j_projects proj
    JOIN staging.neo4j_relationships rel_proj ON proj.project_id = rel_proj.target_node_id
        AND rel_proj.target_node_type = 'Project'
    JOIN staging.neo4j_experiences exp ON rel_proj.source_node_id = exp.experience_id
    JOIN staging.neo4j_relationships rel_person ON exp.experience_id = rel_person.target_node_id
        AND rel_person.relationship_type = 'EXPERIENCED_IN'
    JOIN staging.neo4j_persons p ON rel_person.source_node_id = p.person_id
    JOIN core.unified_users u ON p.email = u.email
    LEFT JOIN staging.neo4j_relationships rel_comp ON exp.experience_id = rel_comp.source_node_id
        AND rel_comp.relationship_type = 'WORKED_AT'
    LEFT JOIN staging.neo4j_companies c ON rel_comp.target_node_id = c.company_id
    LEFT JOIN staging.neo4j_relationships rel_role ON exp.experience_id = rel_role.source_node_id
        AND rel_role.relationship_type = 'WORKED_AS'
    LEFT JOIN staging.neo4j_roles r ON rel_role.target_node_id = r.role_id
    WHERE rel_proj.relationship_type = 'WORKED_ON'
    GROUP BY proj.project_id, proj.project_name, c.company_id
    """
    execute_transform(conn, "project collaborations", project_collab_sql)
    
    log("✅ Neo4j graph data transformed", 'SUCCESS')

def print_summary():
    """Print transformation summary statistics"""
    elapsed_total = time.time() - stats['start_time']
    
    log("\n" + "="*70, 'INFO')
    log("TRANSFORMATION SUMMARY", 'INFO')
    log("="*70, 'INFO')
    
    log(f"\n⏱️  Total Time: {elapsed_total:.2f}s ({elapsed_total/60:.2f} minutes)", 'INFO')
    log(f"📊 Tables Transformed: {stats['tables_transformed']}", 'INFO')
    log(f"📤 Rows Inserted: {stats['total_rows_inserted']:,}", 'INFO')
    
    if stats['total_rows_inserted'] > 0:
        rows_per_sec = stats['total_rows_inserted'] / elapsed_total
        log(f"🚀 Throughput: {rows_per_sec:.0f} rows/second", 'INFO')
    
    if stats['errors']:
        log(f"\n❌ Errors Encountered: {len(stats['errors'])}", 'ERROR')
        for i, error in enumerate(stats['errors'], 1):
            log(f"  {i}. Step: {error.get('step', 'Unknown')}", 'ERROR')
            log(f"     Error: {error.get('error', 'Unknown')}", 'ERROR')
    else:
        log(f"\n✅ No Errors - Clean Transformation!", 'SUCCESS')
    
    log("\n" + "="*70, 'INFO')

def main():
    stats['start_time'] = time.time()
    
    log("="*70, 'INFO')
    log("ETL TRANSFORM - Staging to Core", 'INFO')
    log("="*70, 'INFO')
    log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'INFO')
    log(f"Strategy: Clean, Unify, Calculate Metrics", 'INFO')
    
    # Connect to analytics database
    log("\n📡 Connecting to analytics database...", 'INFO')
    try:
        conn = get_analytics_db_connection()
        log("Connected to analytics database successfully", 'SUCCESS')
    except Exception as e:
        log(f"Failed to connect to analytics database: {str(e)}", 'ERROR')
        log(f"Traceback:\n{traceback.format_exc()}", 'ERROR')
        return 1
    
    # Run transformations
    try:
        transform_unified_users(conn)
        transform_glossary_terms(conn)
        transform_user_activity_events(conn)
        transform_user_cohorts(conn)
        # NEW: Neo4j graph data transformations
        transform_neo4j_data(conn)
    except KeyboardInterrupt:
        log("\n⚠️  Transformation cancelled by user (Ctrl+C)", 'WARNING')
        conn.close()
        print_summary()
        return 130
    except Exception as e:
        log(f"Unexpected error during transformation: {str(e)}", 'ERROR')
        log(f"Traceback:\n{traceback.format_exc()}", 'ERROR')
        stats['errors'].append({'error': 'Unexpected error', 'details': str(e), 'traceback': traceback.format_exc()})
        conn.close()
        print_summary()
        return 1
    
    conn.close()
    
    # Print summary
    print_summary()
    
    # Determine exit status
    if stats['errors']:
        log("⚠️  Transformation completed with errors", 'WARNING')
        log("\nRecommendation: Review errors above before proceeding", 'WARNING')
        return 1
    else:
        log("✅ TRANSFORMATION COMPLETE - Core data ready!", 'SUCCESS')
        log("\nNext steps:", 'INFO')
        log("  1. View core.unified_users in pgAdmin", 'INFO')
        log("  2. Run aggregations: python scripts/aggregate.py", 'INFO')
        return 0

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
ETL Aggregate Script - Calculate metrics from core data into aggregates

Populates:
1. aggregates.daily_metrics (daily KPIs)
2. aggregates.monthly_metrics (monthly rollups)
3. aggregates.cohort_retention (retention curves)
4. aggregates.user_engagement_levels (materialized view refresh)
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
    'aggregates_created': 0,
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

def check_tables_exist(conn, tables):
    """Return list of schema.table names that do not exist"""
    missing = []
    with conn.cursor() as cursor:
        for schema, table in tables:
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
            if not cursor.fetchone()[0]:
                missing.append(f"{schema}.{table}")
    return missing
def execute_aggregate(conn, description, sql):
    """Execute an aggregation SQL statement"""
    log(f"Aggregating {description}...", 'INFO')
    start = time.time()
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows_affected = cursor.rowcount
        conn.commit()
        
        elapsed = time.time() - start
        log(f"  Aggregated {rows_affected:,} rows in {elapsed:.2f}s", 'SUCCESS')
        stats['total_rows_inserted'] += rows_affected
        stats['aggregates_created'] += 1
        return rows_affected
        
    except Exception as e:
        conn.rollback()
        elapsed = time.time() - start
        error_msg = f"Error aggregating {description} after {elapsed:.2f}s: {str(e)}"
        log(error_msg, 'ERROR')
        log(f"  Traceback:\n{traceback.format_exc()}", 'ERROR')
        stats['errors'].append({'step': description, 'error': str(e), 'traceback': traceback.format_exc()})
        return 0

def aggregate_daily_metrics(conn):
    """Calculate daily metrics from core tables"""
    log("\n" + "="*70, 'INFO')
    log("STEP 1: Calculating Daily Metrics", 'INFO')
    log("="*70, 'INFO')
    
    # Clear existing data
    log("  Clearing aggregates.daily_metrics...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.daily_metrics CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    # Calculate daily metrics
    aggregate_sql = """
    INSERT INTO aggregates.daily_metrics (
        metric_date,
        new_signups,
        total_users,
        total_users_cumulative,
        dau,
        posts_created,
        comments_created,
        votes_cast,
        collections_created,
        views_given,
        active_posters,
        active_commenters,
        active_voters,
        active_collectors,
        finder_active,
        standard_active,
        new_finder_signups,
        new_standard_signups,
        engagement_rate,
        social_engagement_rate
    )
    WITH daily_signups AS (
        SELECT 
            DATE(signup_date) AS signup_date,
            COUNT(*) AS new_users,
            COUNT(*) FILTER (WHERE has_finder = TRUE) AS new_finders,
            COUNT(*) FILTER (WHERE has_finder = FALSE) AS new_standards
        FROM core.unified_users
        WHERE deleted_at IS NULL
            AND is_test_account = FALSE
        GROUP BY DATE(signup_date)
    ),
    daily_activities AS (
        SELECT 
            DATE(activity_date) AS activity_date,
            COUNT(DISTINCT user_id) AS active_users,
            COUNT(*) FILTER (WHERE activity_type = 'post') AS posts,
            COUNT(*) FILTER (WHERE activity_type = 'comment') AS comments,
            COUNT(*) FILTER (WHERE activity_type = 'vote') AS votes,
            COUNT(*) FILTER (WHERE activity_type = 'collection') AS collections,
            COUNT(*) FILTER (WHERE activity_type = 'view') AS views,
            COUNT(DISTINCT user_id) FILTER (WHERE activity_type = 'post') AS posters,
            COUNT(DISTINCT user_id) FILTER (WHERE activity_type = 'comment') AS commenters,
            COUNT(DISTINCT user_id) FILTER (WHERE activity_type = 'vote') AS voters,
            COUNT(DISTINCT user_id) FILTER (WHERE activity_type = 'collection') AS collectors
        FROM core.user_activity_events
        GROUP BY DATE(activity_date)
    ),
    daily_active_by_type AS (
        SELECT 
            DATE(e.activity_date) AS activity_date,
            COUNT(DISTINCT e.user_id) FILTER (WHERE u.has_finder = TRUE) AS finder_active,
            COUNT(DISTINCT e.user_id) FILTER (WHERE u.has_finder = FALSE) AS standard_active
        FROM core.user_activity_events e
        JOIN core.unified_users u ON e.user_id = u.chemlink_id
        WHERE u.deleted_at IS NULL
            AND u.is_test_account = FALSE
        GROUP BY DATE(e.activity_date)
    ),
    date_series AS (
        SELECT generate_series(
            (SELECT MIN(DATE(signup_date)) FROM core.unified_users),
            CURRENT_DATE,
            '1 day'::interval
        )::DATE AS metric_date
    ),
    cumulative_users AS (
        SELECT 
            ds.metric_date,
            COUNT(*) AS total_users_cumulative
        FROM date_series ds
        LEFT JOIN core.unified_users u ON DATE(u.signup_date) <= ds.metric_date
        WHERE u.deleted_at IS NULL
            AND u.is_test_account = FALSE
        GROUP BY ds.metric_date
    )
    SELECT 
        ds.metric_date,
        COALESCE(s.new_users, 0) AS new_signups,
        COALESCE(s.new_users, 0) AS total_users,
        COALESCE(cu.total_users_cumulative, 0) AS total_users_cumulative,
        COALESCE(a.active_users, 0) AS dau,
        COALESCE(a.posts, 0) AS posts_created,
        COALESCE(a.comments, 0) AS comments_created,
        COALESCE(a.votes, 0) AS votes_cast,
        COALESCE(a.collections, 0) AS collections_created,
        COALESCE(a.views, 0) AS views_given,
        COALESCE(a.posters, 0) AS active_posters,
        COALESCE(a.commenters, 0) AS active_commenters,
        COALESCE(a.voters, 0) AS active_voters,
        COALESCE(a.collectors, 0) AS active_collectors,
        COALESCE(abt.finder_active, 0) AS finder_active,
        COALESCE(abt.standard_active, 0) AS standard_active,
        COALESCE(s.new_finders, 0) AS new_finder_signups,
        COALESCE(s.new_standards, 0) AS new_standard_signups,
        CASE 
            WHEN cu.total_users_cumulative > 0 
            THEN ROUND((a.active_users::NUMERIC / cu.total_users_cumulative) * 100, 2)
            ELSE 0 
        END AS engagement_rate,
        CASE 
            WHEN a.active_users > 0 
            THEN ROUND(((a.posters + a.commenters)::NUMERIC / a.active_users) * 100, 2)
            ELSE 0 
        END AS social_engagement_rate
    FROM date_series ds
    LEFT JOIN daily_signups s ON ds.metric_date = s.signup_date
    LEFT JOIN daily_activities a ON ds.metric_date = a.activity_date
    LEFT JOIN daily_active_by_type abt ON ds.metric_date = abt.activity_date
    LEFT JOIN cumulative_users cu ON ds.metric_date = cu.metric_date
    ORDER BY ds.metric_date;
    """
    
    return execute_aggregate(conn, "aggregates.daily_metrics", aggregate_sql)

def aggregate_monthly_metrics(conn):
    """Calculate monthly rollups from daily metrics"""
    log("\n" + "="*70, 'INFO')
    log("STEP 2: Calculating Monthly Metrics", 'INFO')
    log("="*70, 'INFO')
    
    # Clear existing data
    log("  Clearing aggregates.monthly_metrics...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.monthly_metrics CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    # Calculate monthly metrics
    aggregate_sql = """
    INSERT INTO aggregates.monthly_metrics (
        metric_month,
        new_signups,
        total_users_end_of_month,
        growth_rate_pct,
        mau,
        avg_dau,
        total_posts,
        total_comments,
        total_votes,
        total_collections,
        activation_rate,
        avg_activities_per_user,
        avg_engagement_score,
        finder_mau,
        standard_mau,
        finder_adoption_pct,
        retained_from_prev_month,
        retention_rate
    )
    WITH monthly_rollup AS (
        SELECT 
            DATE_TRUNC('month', metric_date)::DATE AS metric_month,
            SUM(new_signups) AS new_signups,
            MAX(total_users_cumulative) AS total_users_end_of_month,
            COUNT(DISTINCT CASE WHEN dau > 0 THEN metric_date END) AS active_days,
            COUNT(DISTINCT metric_date) AS total_days,
            AVG(dau) AS avg_dau,
            SUM(posts_created) AS total_posts,
            SUM(comments_created) AS total_comments,
            SUM(votes_cast) AS total_votes,
            SUM(collections_created) AS total_collections,
            MAX(finder_active) AS finder_mau,
            MAX(standard_active) AS standard_mau
        FROM aggregates.daily_metrics
        GROUP BY DATE_TRUNC('month', metric_date)
    ),
    monthly_activity_users AS (
        SELECT 
            DATE_TRUNC('month', e.activity_date)::DATE AS metric_month,
            COUNT(DISTINCT e.user_id) AS mau,
            COUNT(*) AS total_activities
        FROM core.user_activity_events e
        JOIN core.unified_users u ON e.user_id = u.chemlink_id
        WHERE u.deleted_at IS NULL
            AND u.is_test_account = FALSE
        GROUP BY DATE_TRUNC('month', e.activity_date)
    ),
    monthly_activation AS (
        SELECT 
            DATE_TRUNC('month', signup_date)::DATE AS metric_month,
            COUNT(*) AS cohort_users,
            COUNT(*) FILTER (WHERE activation_status = TRUE) AS activated_users
        FROM core.unified_users
        WHERE deleted_at IS NULL
            AND is_test_account = FALSE
        GROUP BY DATE_TRUNC('month', signup_date)
    ),
    prev_month_retention AS (
        SELECT 
            DATE_TRUNC('month', CURRENT_DATE)::DATE AS metric_month,
            COUNT(DISTINCT e.user_id) AS retained_from_prev
        FROM core.user_activity_events e
        WHERE DATE_TRUNC('month', e.activity_date) = DATE_TRUNC('month', CURRENT_DATE)
            AND EXISTS (
                SELECT 1 FROM core.user_activity_events e2
                WHERE e2.user_id = e.user_id
                    AND DATE_TRUNC('month', e2.activity_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
            )
    )
    SELECT 
        r.metric_month,
        r.new_signups,
        r.total_users_end_of_month,
        CASE 
            WHEN LAG(r.total_users_end_of_month) OVER (ORDER BY r.metric_month) > 0
            THEN ROUND(((r.total_users_end_of_month - LAG(r.total_users_end_of_month) OVER (ORDER BY r.metric_month))::NUMERIC / 
                       LAG(r.total_users_end_of_month) OVER (ORDER BY r.metric_month)) * 100, 2)
            ELSE 0
        END AS growth_rate_pct,
        COALESCE(mau.mau, 0) AS mau,
        ROUND(r.avg_dau, 2) AS avg_dau,
        r.total_posts,
        r.total_comments,
        r.total_votes,
        r.total_collections,
        CASE 
            WHEN act.cohort_users > 0
            THEN ROUND((act.activated_users::NUMERIC / act.cohort_users) * 100, 2)
            ELSE 0
        END AS activation_rate,
        CASE 
            WHEN mau.mau > 0
            THEN ROUND(mau.total_activities::NUMERIC / mau.mau, 2)
            ELSE 0
        END AS avg_activities_per_user,
        CASE 
            WHEN mau.mau > 0
            THEN ROUND((r.total_posts * 3 + r.total_comments * 2 + r.total_votes + r.total_collections * 5)::NUMERIC / mau.mau, 2)
            ELSE 0
        END AS avg_engagement_score,
        COALESCE(r.finder_mau, 0) AS finder_mau,
        COALESCE(r.standard_mau, 0) AS standard_mau,
        CASE 
            WHEN r.total_users_end_of_month > 0
            THEN ROUND((r.finder_mau::NUMERIC / r.total_users_end_of_month) * 100, 2)
            ELSE 0
        END AS finder_adoption_pct,
        COALESCE(ret.retained_from_prev, 0) AS retained_from_prev_month,
        CASE 
            WHEN LAG(mau.mau) OVER (ORDER BY r.metric_month) > 0
            THEN ROUND((ret.retained_from_prev::NUMERIC / LAG(mau.mau) OVER (ORDER BY r.metric_month)) * 100, 2)
            ELSE 0
        END AS retention_rate
    FROM monthly_rollup r
    LEFT JOIN monthly_activity_users mau ON r.metric_month = mau.metric_month
    LEFT JOIN monthly_activation act ON r.metric_month = act.metric_month
    LEFT JOIN prev_month_retention ret ON r.metric_month = ret.metric_month
    ORDER BY r.metric_month;
    """
    
    return execute_aggregate(conn, "aggregates.monthly_metrics", aggregate_sql)

def aggregate_cohort_retention(conn):
    """Calculate cohort retention curves"""
    log("\n" + "="*70, 'INFO')
    log("STEP 3: Calculating Cohort Retention", 'INFO')
    log("="*70, 'INFO')
    
    # Clear existing data
    log("  Clearing aggregates.cohort_retention...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.cohort_retention CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    # Calculate cohort retention
    aggregate_sql = """
    INSERT INTO aggregates.cohort_retention (
        cohort_month,
        weeks_since_signup,
        total_users,
        retained_users,
        retention_rate,
        cumulative_retention,
        avg_activities_per_user,
        total_activities
    )
    WITH cohort_base AS (
        SELECT 
            DATE_TRUNC('month', signup_date)::DATE AS cohort_month,
            chemlink_id,
            signup_date
        FROM core.unified_users
        WHERE deleted_at IS NULL
            AND is_test_account = FALSE
    ),
    week_series AS (
        SELECT generate_series(0, 52) AS weeks_since_signup
    ),
    cohort_weeks AS (
        SELECT 
            cb.cohort_month,
            ws.weeks_since_signup,
            cb.chemlink_id,
            cb.signup_date,
            cb.signup_date + (ws.weeks_since_signup * INTERVAL '1 week') AS week_start,
            cb.signup_date + ((ws.weeks_since_signup + 1) * INTERVAL '1 week') AS week_end
        FROM cohort_base cb
        CROSS JOIN week_series ws
        WHERE cb.signup_date + (ws.weeks_since_signup * INTERVAL '1 week') <= CURRENT_DATE
    ),
    cohort_activity AS (
        SELECT 
            cw.cohort_month,
            cw.weeks_since_signup,
            cw.chemlink_id,
            COUNT(e.id) AS activities
        FROM cohort_weeks cw
        LEFT JOIN core.user_activity_events e ON 
            cw.chemlink_id = e.user_id
            AND e.activity_date >= cw.week_start
            AND e.activity_date < cw.week_end
        GROUP BY cw.cohort_month, cw.weeks_since_signup, cw.chemlink_id
    )
    SELECT 
        cohort_month,
        weeks_since_signup,
        COUNT(DISTINCT chemlink_id) AS total_users,
        COUNT(DISTINCT chemlink_id) FILTER (WHERE activities > 0) AS retained_users,
        ROUND((COUNT(DISTINCT chemlink_id) FILTER (WHERE activities > 0)::NUMERIC / COUNT(DISTINCT chemlink_id)) * 100, 2) AS retention_rate,
        ROUND((COUNT(DISTINCT chemlink_id) FILTER (WHERE activities > 0)::NUMERIC / 
               FIRST_VALUE(COUNT(DISTINCT chemlink_id)) OVER (PARTITION BY cohort_month ORDER BY weeks_since_signup)) * 100, 2) AS cumulative_retention,
        ROUND(AVG(activities) FILTER (WHERE activities > 0), 2) AS avg_activities_per_user,
        SUM(activities) AS total_activities
    FROM cohort_activity
    GROUP BY cohort_month, weeks_since_signup
    HAVING COUNT(DISTINCT chemlink_id) > 0
    ORDER BY cohort_month DESC, weeks_since_signup;
    """
    
    return execute_aggregate(conn, "aggregates.cohort_retention", aggregate_sql)

def aggregate_post_metrics(conn):
    """Calculate post engagement metrics"""
    log("\n" + "="*70, 'INFO')
    log("STEP 4: Calculating Post Metrics", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.post_metrics...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.post_metrics CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.post_metrics (
        metric_date, posts_created, comments_created, unique_posters, unique_commenters,
        avg_posts_per_poster, avg_comments_per_post, avg_votes_per_post, 
        engagement_rate_comments_pct, engagement_rate_votes_pct, total_votes,
        text_posts, link_posts, media_posts
    )
    WITH post_data AS (
        SELECT 
            DATE(activity_date) AS metric_date,
            COUNT(*) FILTER (WHERE activity_type = 'post') AS posts_created,
            COUNT(*) FILTER (WHERE activity_type = 'comment') AS comments_created,
            COUNT(*) FILTER (WHERE activity_type = 'vote') AS votes_created,
            COUNT(DISTINCT user_id) FILTER (WHERE activity_type = 'post') AS unique_posters,
            COUNT(DISTINCT user_id) FILTER (WHERE activity_type = 'comment') AS unique_commenters,
            COUNT(*) FILTER (WHERE activity_type = 'post' AND metadata->>'has_link' = 'false' AND metadata->>'has_media' = 'false') AS text_posts,
            COUNT(*) FILTER (WHERE activity_type = 'post' AND metadata->>'has_link' = 'true') AS link_posts,
            COUNT(*) FILTER (WHERE activity_type = 'post' AND metadata->>'has_media' = 'true') AS media_posts
        FROM core.user_activity_events
        WHERE activity_type IN ('post', 'comment', 'vote')
        GROUP BY DATE(activity_date)
    )
    SELECT 
        metric_date,
        posts_created,
        comments_created,
        unique_posters,
        unique_commenters,
        ROUND(posts_created::NUMERIC / NULLIF(unique_posters, 0), 2) AS avg_posts_per_poster,
        ROUND(comments_created::NUMERIC / NULLIF(posts_created, 0), 2) AS avg_comments_per_post,
        ROUND(votes_created::NUMERIC / NULLIF(posts_created, 0), 2) AS avg_votes_per_post,
        ROUND((comments_created::NUMERIC / NULLIF(posts_created, 0)) * 100, 2) AS engagement_rate_comments_pct,
        ROUND((votes_created::NUMERIC / NULLIF(posts_created, 0)) * 100, 2) AS engagement_rate_votes_pct,
        votes_created AS total_votes,
        text_posts,
        link_posts,
        media_posts
    FROM post_data
    ORDER BY metric_date;
    """
    
    return execute_aggregate(conn, "aggregates.post_metrics", aggregate_sql)

def aggregate_finder_metrics(conn):
    """Calculate finder search and vote metrics"""
    log("\n" + "="*70, 'INFO')
    log("STEP 5: Calculating Finder Metrics", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.finder_metrics...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.finder_metrics CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.finder_metrics (
        metric_date, total_votes, unique_voters, profiles_viewed, unique_profile_viewers
    )
    SELECT 
        DATE(e.activity_date) AS metric_date,
        COUNT(*) FILTER (WHERE e.activity_type = 'vote') AS total_votes,
        COUNT(DISTINCT e.user_id) FILTER (WHERE e.activity_type = 'vote') AS unique_voters,
        COUNT(*) FILTER (WHERE e.activity_type = 'view') AS profiles_viewed,
        COUNT(DISTINCT e.user_id) FILTER (WHERE e.activity_type = 'view') AS unique_profile_viewers
    FROM core.user_activity_events e
    WHERE e.activity_type IN ('vote', 'view')
    GROUP BY DATE(e.activity_date)
    ORDER BY metric_date;
    """
    
    return execute_aggregate(conn, "aggregates.finder_metrics", aggregate_sql)

def aggregate_collection_metrics(conn):
    """Calculate collection creation and usage metrics"""
    log("\n" + "="*70, 'INFO')
    log("STEP 6: Calculating Collection Metrics", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.collection_metrics...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.collection_metrics CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.collection_metrics (
        metric_date, total_collections_created, public_collections, private_collections, unique_collectors
    )
    SELECT 
        DATE(e.activity_date) AS metric_date,
        COUNT(*) AS total_collections_created,
        COUNT(*) FILTER (WHERE e.metadata->>'privacy' = 'PUBLIC') AS public_collections,
        COUNT(*) FILTER (WHERE e.metadata->>'privacy' = 'PRIVATE') AS private_collections,
        COUNT(DISTINCT e.user_id) AS unique_collectors
    FROM core.user_activity_events e
    WHERE e.activity_type = 'collection'
    GROUP BY DATE(e.activity_date)
    ORDER BY metric_date;
    """
    
    return execute_aggregate(conn, "aggregates.collection_metrics", aggregate_sql)

def aggregate_profile_metrics(conn):
    """Calculate profile update metrics"""
    log("\n" + "="*70, 'INFO')
    log("STEP 7: Calculating Profile Metrics", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.profile_metrics...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.profile_metrics CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.profile_metrics (
        metric_date, profiles_updated, experiences_added, education_added,
        avg_profile_completion_score, profiles_with_headline, profiles_with_linkedin,
        profiles_with_location, profiles_with_experience, profiles_with_education
    )
    -- Just insert current snapshot
    SELECT 
        CURRENT_DATE AS metric_date,
        (SELECT COUNT(*) FROM staging.chemlink_persons 
         WHERE deleted_at IS NULL AND DATE(updated_at) = CURRENT_DATE AND updated_at != created_at) AS profiles_updated,
        (SELECT COUNT(*) FROM staging.chemlink_experiences 
         WHERE deleted_at IS NULL AND DATE(created_at) = CURRENT_DATE) AS experiences_added,
        (SELECT COUNT(*) FROM staging.chemlink_education 
         WHERE deleted_at IS NULL AND DATE(created_at) = CURRENT_DATE) AS education_added,
        ROUND(AVG(u.profile_completion_score), 2) AS avg_profile_completion_score,
        COUNT(*) FILTER (WHERE p.headline_description IS NOT NULL) AS profiles_with_headline,
        COUNT(*) FILTER (WHERE p.linked_in_url IS NOT NULL) AS profiles_with_linkedin,
        COUNT(*) FILTER (WHERE p.location_id IS NOT NULL) AS profiles_with_location,
        COUNT(*) FILTER (WHERE u.experience_count > 0) AS profiles_with_experience,
        COUNT(*) FILTER (WHERE u.education_count > 0) AS profiles_with_education
    FROM core.unified_users u
    JOIN staging.chemlink_persons p ON u.chemlink_id = p.id
    WHERE u.deleted_at IS NULL AND u.is_test_account = FALSE;
    """
    
    return execute_aggregate(conn, "aggregates.profile_metrics", aggregate_sql)

def aggregate_funnel_metrics(conn):
    """Calculate account creation funnel metrics"""
    log("\n" + "="*70, 'INFO')
    log("STEP 8: Calculating Funnel Metrics", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.funnel_metrics...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.funnel_metrics CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.funnel_metrics (
        metric_date, total_signups, profiles_with_basic_info, profiles_with_experience,
        profiles_with_education, profiles_completed, profiles_activated,
        basic_info_rate, experience_rate, education_rate, completion_rate, activation_rate
    )
    SELECT 
        CURRENT_DATE AS metric_date,
        COUNT(*) AS total_signups,
        COUNT(*) FILTER (WHERE first_name IS NOT NULL AND last_name IS NOT NULL AND email IS NOT NULL) AS profiles_with_basic_info,
        COUNT(*) FILTER (WHERE experience_count > 0) AS profiles_with_experience,
        COUNT(*) FILTER (WHERE education_count > 0) AS profiles_with_education,
        COUNT(*) FILTER (WHERE profile_completion_score >= 70) AS profiles_completed,
        COUNT(*) FILTER (WHERE activation_status = TRUE) AS profiles_activated,
        ROUND((COUNT(*) FILTER (WHERE first_name IS NOT NULL AND last_name IS NOT NULL)::NUMERIC / COUNT(*)) * 100, 2) AS basic_info_rate,
        ROUND((COUNT(*) FILTER (WHERE experience_count > 0)::NUMERIC / COUNT(*)) * 100, 2) AS experience_rate,
        ROUND((COUNT(*) FILTER (WHERE education_count > 0)::NUMERIC / COUNT(*)) * 100, 2) AS education_rate,
        ROUND((COUNT(*) FILTER (WHERE profile_completion_score >= 70)::NUMERIC / COUNT(*)) * 100, 2) AS completion_rate,
        ROUND((COUNT(*) FILTER (WHERE activation_status = TRUE)::NUMERIC / COUNT(*)) * 100, 2) AS activation_rate
    FROM core.unified_users
    WHERE deleted_at IS NULL AND is_test_account = FALSE;
    """
    
    return execute_aggregate(conn, "aggregates.funnel_metrics", aggregate_sql)

def aggregate_connection_recommendations(conn):
    """Calculate connection recommendations (People You Should Know)"""
    log("\n" + "="*70, 'INFO')
    log("STEP 9: Calculating Connection Recommendations", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.connection_recommendations...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.connection_recommendations CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.connection_recommendations (
        user_id, recommended_user_id, recommendation_score,
        common_companies, common_roles, common_schools, 
        common_locations, recommendation_reason
    )
    WITH base_relationships AS (
        SELECT 
            LEAST(r.user_id, r.related_user_id) as user_id,
            GREATEST(r.user_id, r.related_user_id) as recommended_user_id,
            r.relationship_strength,
            r.connection_context,
            r.relationship_type
        FROM core.user_relationships r
        WHERE r.relationship_strength > 0
    ),
    ranked_relationships AS (
        SELECT 
            user_id,
            recommended_user_id,
            MAX(relationship_strength * 10)::DECIMAL(5,2) as recommendation_score,
            array_agg(DISTINCT relationship_type) as relationship_types
        FROM base_relationships
        GROUP BY user_id, recommended_user_id
    )
    SELECT 
        user_id,
        recommended_user_id,
        recommendation_score,
        '{}' as common_companies,
        '{}' as common_roles,
        '{}' as common_schools,
        '{}' as common_locations,
        CASE 
            WHEN 'WORKED_TOGETHER' = ANY(relationship_types) THEN 'Worked at the same companies'
            WHEN 'STUDIED_TOGETHER' = ANY(relationship_types) THEN 'Studied at the same schools'
            ELSE 'Have connections in common'
        END as recommendation_reason
    FROM ranked_relationships
    ORDER BY recommendation_score DESC
    LIMIT 100000
    """
    
    return execute_aggregate(conn, "aggregates.connection_recommendations", aggregate_sql)

def aggregate_company_network_map(conn):
    """Build company network map"""
    log("\n" + "="*70, 'INFO')
    log("STEP 10: Building Company Network Map", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.company_network_map...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.company_network_map CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.company_network_map (
        company_id_1, company_id_2, company_name_1, company_name_2,
        shared_employee_count, employee_ids, network_strength_score
    )
    SELECT 
        cn1.company_id as company_id_1,
        cn2.company_id as company_id_2,
        cn1.company_name as company_name_1,
        cn2.company_name as company_name_2,
        COUNT(DISTINCT u.user_id) as shared_employee_count,
        array_agg(DISTINCT u.user_id) as employee_ids,
        (COUNT(DISTINCT u.user_id) * 1.0)::DECIMAL(5,2) as network_strength_score
    FROM core.company_networks cn1
    CROSS JOIN LATERAL unnest(cn1.user_ids) AS u(user_id)
    JOIN core.company_networks cn2 ON u.user_id = ANY(cn2.user_ids)
        AND cn1.company_id < cn2.company_id
    GROUP BY cn1.company_id, cn1.company_name, cn2.company_id, cn2.company_name
    HAVING COUNT(DISTINCT u.user_id) > 0
    ORDER BY shared_employee_count DESC
    LIMIT 10000
    """
    
    return execute_aggregate(conn, "aggregates.company_network_map", aggregate_sql)

def aggregate_skills_matching(conn):
    """Calculate skills/role similarity scores"""
    log("\n" + "="*70, 'INFO')
    log("STEP 11: Calculating Skills Matching Scores", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.skills_matching_scores...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.skills_matching_scores CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.skills_matching_scores (
        user_id, role_id, role_title, experience_years,
        proficiency_score, similar_user_ids, similar_user_count
    )
    SELECT DISTINCT ON (u.user_id, cn.role_id)
        u.user_id,
        cn.role_id,
        cn.role_title,
        LEAST(EXTRACT(YEAR FROM AGE(CURRENT_DATE, uu.signup_date)), 50)::DECIMAL(4,1) as experience_years,
        LEAST((uu.experience_count * 10 + uu.profile_completion_score / 10), 999)::DECIMAL(5,2) as proficiency_score,
        cn.user_ids as similar_user_ids,
        cn.user_count as similar_user_count
    FROM (SELECT DISTINCT unnest(user_ids) as user_id FROM core.company_networks) u
    JOIN core.unified_users uu ON u.user_id = uu.chemlink_id
    JOIN core.company_networks cn ON u.user_id = ANY(cn.user_ids)
    WHERE cn.role_id IS NOT NULL
    ORDER BY u.user_id, cn.role_id, proficiency_score DESC
    LIMIT 50000
    """
    
    return execute_aggregate(conn, "aggregates.skills_matching_scores", aggregate_sql)

def aggregate_career_path_patterns(conn):
    """Identify common career progression patterns"""
    log("\n" + "="*70, 'INFO')
    log("STEP 12: Analyzing Career Path Patterns", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.career_path_patterns...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.career_path_patterns CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    # For now, create placeholder patterns based on role groupings
    aggregate_sql = """
    INSERT INTO aggregates.career_path_patterns (
        path_vector, path_hash, role_sequence, user_count, user_ids, avg_years_per_role
    )
    SELECT 
        array_to_string(array_agg(DISTINCT cn.role_title ORDER BY cn.role_title), ' -> ') as path_vector,
        hashtextextended(
            COALESCE(array_to_string(array_agg(DISTINCT cn.role_title ORDER BY cn.role_title), ' -> '), ''),
            0
        )::text as path_hash,
        array_agg(DISTINCT cn.role_title ORDER BY cn.role_title) as role_sequence,
        COUNT(DISTINCT u.user_id) as user_count,
        array_agg(DISTINCT u.user_id) as user_ids,
        2.5 as avg_years_per_role
    FROM (SELECT DISTINCT unnest(user_ids) as user_id FROM core.company_networks) u
    JOIN core.company_networks cn ON u.user_id = ANY(cn.user_ids)
    WHERE cn.role_title IS NOT NULL
    GROUP BY cn.company_id
    HAVING COUNT(DISTINCT u.user_id) >= 2
    ORDER BY user_count DESC
    LIMIT 1000
    """
    
    return execute_aggregate(conn, "aggregates.career_path_patterns", aggregate_sql)

def aggregate_location_networks(conn):
    """Aggregate location-based networks"""
    log("\n" + "="*70, 'INFO')
    log("STEP 13: Building Location Networks", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.location_based_networks...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.location_based_networks CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.location_based_networks (
        location_id, country, user_ids, user_count,
        company_diversity_score, role_diversity_score,
        top_companies, top_roles
    )
    SELECT 
        ln.location_id,
        ln.country,
        ln.user_ids,
        ln.user_count,
        (SELECT COUNT(DISTINCT cn.company_id)::DECIMAL(5,2)
         FROM core.company_networks cn
         WHERE cn.user_ids && ln.user_ids
        ) as company_diversity_score,
        (SELECT COUNT(DISTINCT cn.role_id)::DECIMAL(5,2)
         FROM core.company_networks cn
         WHERE cn.user_ids && ln.user_ids AND cn.role_id IS NOT NULL
        ) as role_diversity_score,
        (SELECT array_agg(sub.company_name ORDER BY sub.user_count DESC)
         FROM (
             SELECT DISTINCT ON (cn.company_name) cn.company_name, cn.user_count
             FROM core.company_networks cn
             WHERE cn.user_ids && ln.user_ids
             ORDER BY cn.company_name, cn.user_count DESC
             LIMIT 10
         ) sub
        ) as top_companies,
        (SELECT array_agg(sub.role_title ORDER BY sub.user_count DESC)
         FROM (
             SELECT DISTINCT ON (cn.role_title) cn.role_title, cn.user_count
             FROM core.company_networks cn
             WHERE cn.user_ids && ln.user_ids AND cn.role_title IS NOT NULL
             ORDER BY cn.role_title, cn.user_count DESC
             LIMIT 10
         ) sub
        ) as top_roles
    FROM core.location_networks ln
    WHERE ln.user_count > 0
    ORDER BY ln.user_count DESC
    """
    
    return execute_aggregate(conn, "aggregates.location_based_networks", aggregate_sql)

def aggregate_alumni_networks(conn):
    """Build alumni networks by school"""
    log("\n" + "="*70, 'INFO')
    log("STEP 14: Building Alumni Networks", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.alumni_networks...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.alumni_networks CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.alumni_networks (
        school_id, school_name, degree_id, degree_name,
        user_ids, alumni_count, graduation_year_min, graduation_year_max,
        current_companies, current_roles
    )
    SELECT 
        en.school_id,
        en.school_name,
        COALESCE(en.degree_id, 'ALL') as degree_id,
        en.degree_name,
        en.user_ids,
        en.user_count as alumni_count,
        en.graduation_year_min,
        en.graduation_year_max,
        (SELECT array_agg(sub.company_name ORDER BY sub.user_count DESC)
         FROM (
             SELECT DISTINCT ON (cn.company_name) cn.company_name, cn.user_count
             FROM core.company_networks cn
             WHERE cn.user_ids && en.user_ids
             ORDER BY cn.company_name, cn.user_count DESC
             LIMIT 10
         ) sub
        ) as current_companies,
        (SELECT array_agg(sub.role_title ORDER BY sub.user_count DESC)
         FROM (
             SELECT DISTINCT ON (cn.role_title) cn.role_title, cn.user_count
             FROM core.company_networks cn
             WHERE cn.user_ids && en.user_ids AND cn.role_title IS NOT NULL
             ORDER BY cn.role_title, cn.user_count DESC
             LIMIT 10
         ) sub
        ) as current_roles
    FROM core.education_networks en
    WHERE en.user_count > 0
    ORDER BY en.user_count DESC
    """
    
    return execute_aggregate(conn, "aggregates.alumni_networks", aggregate_sql)

def aggregate_project_collaborations(conn):
    """Map project collaboration networks"""
    log("\n" + "="*70, 'INFO')
    log("STEP 15: Mapping Project Collaborations", 'INFO')
    log("="*70, 'INFO')
    
    log("  Clearing aggregates.project_collaboration_graph...", 'INFO')
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE aggregates.project_collaboration_graph CASCADE")
    conn.commit()
    log("  Table cleared", 'SUCCESS')
    
    aggregate_sql = """
    INSERT INTO aggregates.project_collaboration_graph (
        project_id, project_name, company_id, company_name,
        user_ids, user_count, role_ids, collaboration_strength
    )
    SELECT 
        pc.project_id,
        pc.project_name,
        pc.company_id,
        (SELECT cn.company_name FROM core.company_networks cn 
         WHERE cn.company_id = pc.company_id LIMIT 1) as company_name,
        pc.user_ids,
        pc.user_count,
        pc.role_ids,
        (pc.user_count * 1.0)::DECIMAL(5,2) as collaboration_strength
    FROM core.project_collaborations pc
    WHERE pc.user_count > 0
    ORDER BY pc.user_count DESC
    """
    
    return execute_aggregate(conn, "aggregates.project_collaboration_graph", aggregate_sql)

def refresh_materialized_views(conn):
    """Refresh materialized views"""
    log("\n" + "="*70, 'INFO')
    log("STEP 16: Refreshing Materialized Views", 'INFO')
    log("="*70, 'INFO')
    
    log("  Refreshing aggregates.user_engagement_levels...", 'INFO')
    start = time.time()
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW aggregates.user_engagement_levels")
            cursor.execute("SELECT COUNT(*) FROM aggregates.user_engagement_levels")
            row_count = cursor.fetchone()[0]
        conn.commit()
        
        elapsed = time.time() - start
        log(f"  Refreshed materialized view: {row_count:,} rows in {elapsed:.2f}s", 'SUCCESS')
        stats['total_rows_inserted'] += row_count
        stats['aggregates_created'] += 1
        return row_count
        
    except Exception as e:
        conn.rollback()
        elapsed = time.time() - start
        error_msg = f"Error refreshing materialized view after {elapsed:.2f}s: {str(e)}"
        log(error_msg, 'ERROR')
        log(f"  Traceback:\n{traceback.format_exc()}", 'ERROR')
        stats['errors'].append({'step': 'materialized view refresh', 'error': str(e), 'traceback': traceback.format_exc()})
        return 0

def print_summary():
    """Print aggregation summary statistics"""
    elapsed_total = time.time() - stats['start_time']
    
    log("\n" + "="*70, 'INFO')
    log("AGGREGATION SUMMARY", 'INFO')
    log("="*70, 'INFO')
    
    log(f"\n⏱️  Total Time: {elapsed_total:.2f}s ({elapsed_total/60:.2f} minutes)", 'INFO')
    log(f"📊 Aggregates Created: {stats['aggregates_created']}", 'INFO')
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
        log(f"\n✅ No Errors - Clean Aggregation!", 'SUCCESS')
    
    log("\n" + "="*70, 'INFO')

def main():
    stats['start_time'] = time.time()
    
    log("="*70, 'INFO')
    log("ETL AGGREGATE - Core to Aggregates", 'INFO')
    log("="*70, 'INFO')
    log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'INFO')
    log(f"Strategy: Pre-calculate metrics for fast dashboard queries", 'INFO')
    
    # Connect to analytics database
    log("\n📡 Connecting to analytics database...", 'INFO')
    try:
        conn = get_analytics_db_connection()
        log("Connected to analytics database successfully", 'SUCCESS')
    except Exception as e:
        log(f"Failed to connect to analytics database: {str(e)}", 'ERROR')
        log(f"Traceback:\n{traceback.format_exc()}", 'ERROR')
        return 1
    
    # Run aggregations
    try:
        aggregate_daily_metrics(conn)
        aggregate_monthly_metrics(conn)
        aggregate_cohort_retention(conn)
        aggregate_post_metrics(conn)
        aggregate_finder_metrics(conn)
        aggregate_collection_metrics(conn)
        aggregate_profile_metrics(conn)
        aggregate_funnel_metrics(conn)
        
        neo4j_required_tables = [
            ('core', 'user_relationships'),
            ('core', 'company_networks'),
            ('core', 'career_paths'),
            ('core', 'education_networks'),
            ('core', 'location_networks'),
            ('core', 'project_collaborations'),
            ('aggregates', 'connection_recommendations'),
            ('aggregates', 'company_network_map'),
            ('aggregates', 'skills_matching_scores'),
            ('aggregates', 'career_path_patterns'),
            ('aggregates', 'location_based_networks'),
            ('aggregates', 'alumni_networks'),
            ('aggregates', 'project_collaboration_graph')
        ]
        missing_neo4j_tables = check_tables_exist(conn, neo4j_required_tables)
        
        if missing_neo4j_tables:
            log("\n⚠️  Neo4j integration tables not found; skipping advanced graph aggregates (Steps 9-15)", 'WARNING')
            log(f"   Missing tables: {', '.join(missing_neo4j_tables)}", 'WARNING')
        else:
            aggregate_connection_recommendations(conn)
            aggregate_company_network_map(conn)
            aggregate_skills_matching(conn)
            aggregate_career_path_patterns(conn)
            aggregate_location_networks(conn)
            aggregate_alumni_networks(conn)
            aggregate_project_collaborations(conn)
        
        refresh_materialized_views(conn)
    except KeyboardInterrupt:
        log("\n⚠️  Aggregation cancelled by user (Ctrl+C)", 'WARNING')
        conn.close()
        print_summary()
        return 130
    except Exception as e:
        log(f"Unexpected error during aggregation: {str(e)}", 'ERROR')
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
        log("⚠️  Aggregation completed with errors", 'WARNING')
        log("\nRecommendation: Review errors above before proceeding", 'WARNING')
        return 1
    else:
        log("✅ AGGREGATION COMPLETE - Dashboard-ready data!", 'SUCCESS')
        log("\nNext steps:", 'INFO')
        log("  1. View aggregates.daily_metrics for daily KPIs", 'INFO')
        log("  2. View aggregates.user_engagement_levels for user segments", 'INFO')
        log("  3. Build dashboard with pre-calculated metrics", 'INFO')
        return 0

if __name__ == '__main__':
    sys.exit(main())

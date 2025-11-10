-- ==============================================================================
-- ChemLink Analytics Database - Aggregates Schema
-- ==============================================================================
-- Purpose: Pre-calculated metrics for fast dashboard queries
-- Schema: aggregates
-- Refresh Strategy: Daily/Weekly/Monthly depending on table
-- ==============================================================================

-- ==============================================================================
-- aggregates.daily_metrics - DAILY KPIS
-- ==============================================================================
-- Purpose: Pre-calculated daily metrics for dashboards
-- Source: core.unified_users + core.user_activity_events
-- Refresh: Daily at 1 AM
-- ==============================================================================

CREATE TABLE aggregates.daily_metrics (
    metric_date DATE PRIMARY KEY,
    
    -- Growth metrics
    new_signups INT DEFAULT 0,
    total_users INT DEFAULT 0,
    total_users_cumulative INT DEFAULT 0,
    
    -- Activity metrics
    dau INT DEFAULT 0, -- Daily Active Users (any activity)
    posts_created INT DEFAULT 0,
    comments_created INT DEFAULT 0,
    votes_cast INT DEFAULT 0,
    collections_created INT DEFAULT 0,
    views_given INT DEFAULT 0,
    
    -- Engagement breakdown
    active_posters INT DEFAULT 0,
    active_commenters INT DEFAULT 0,
    active_voters INT DEFAULT 0,
    active_collectors INT DEFAULT 0,
    
    -- User type breakdown
    finder_active INT DEFAULT 0,
    standard_active INT DEFAULT 0,
    new_finder_signups INT DEFAULT 0,
    new_standard_signups INT DEFAULT 0,
    
    -- Calculated rates
    engagement_rate DECIMAL(5,2) DEFAULT 0, -- DAU / Total Users
    social_engagement_rate DECIMAL(5,2) DEFAULT 0, -- Posters+Commenters / DAU
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_daily_metrics_date ON aggregates.daily_metrics(metric_date);
CREATE INDEX idx_daily_metrics_dau ON aggregates.daily_metrics(dau);

COMMENT ON TABLE aggregates.daily_metrics IS 'Daily KPIs for dashboard';

-- ==============================================================================
-- aggregates.monthly_metrics - MONTHLY ROLLUPS
-- ==============================================================================
-- Purpose: Monthly aggregated metrics
-- Source: aggregates.daily_metrics (rolled up)
-- Refresh: Monthly on the 1st
-- ==============================================================================

CREATE TABLE aggregates.monthly_metrics (
    metric_month DATE PRIMARY KEY,
    
    -- Growth metrics
    new_signups INT DEFAULT 0,
    total_users_end_of_month INT DEFAULT 0,
    growth_rate_pct DECIMAL(5,2) DEFAULT 0,
    
    -- Activity metrics
    mau INT DEFAULT 0, -- Monthly Active Users
    avg_dau DECIMAL(8,2) DEFAULT 0,
    total_posts INT DEFAULT 0,
    total_comments INT DEFAULT 0,
    total_votes INT DEFAULT 0,
    total_collections INT DEFAULT 0,
    
    -- Engagement metrics
    activation_rate DECIMAL(5,2) DEFAULT 0, -- Activated / Total Users
    avg_activities_per_user DECIMAL(8,2) DEFAULT 0,
    avg_engagement_score DECIMAL(8,2) DEFAULT 0,
    
    -- User type breakdown
    finder_mau INT DEFAULT 0,
    standard_mau INT DEFAULT 0,
    finder_adoption_pct DECIMAL(5,2) DEFAULT 0,
    
    -- Retention
    retained_from_prev_month INT DEFAULT 0,
    retention_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_monthly_metrics_month ON aggregates.monthly_metrics(metric_month);
CREATE INDEX idx_monthly_metrics_mau ON aggregates.monthly_metrics(mau);

COMMENT ON TABLE aggregates.monthly_metrics IS 'Monthly rolled-up metrics';

-- ==============================================================================
-- aggregates.cohort_retention - COHORT RETENTION ANALYSIS
-- ==============================================================================
-- Purpose: Retention rates by signup cohort over time
-- Source: core.user_cohorts + core.user_activity_events
-- Refresh: Weekly
-- ==============================================================================

CREATE TABLE aggregates.cohort_retention (
    cohort_month DATE NOT NULL,
    weeks_since_signup INT NOT NULL,
    
    -- Cohort metrics
    total_users INT DEFAULT 0,
    retained_users INT DEFAULT 0,  -- Active in this week
    retention_rate DECIMAL(5,2) DEFAULT 0,
    cumulative_retention DECIMAL(5,2) DEFAULT 0,
    
    -- Activity metrics
    avg_activities_per_user DECIMAL(8,2) DEFAULT 0,
    total_activities INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (cohort_month, weeks_since_signup)
);

CREATE INDEX idx_cohort_retention_month ON aggregates.cohort_retention(cohort_month);
CREATE INDEX idx_cohort_retention_weeks ON aggregates.cohort_retention(weeks_since_signup);
CREATE INDEX idx_cohort_retention_rate ON aggregates.cohort_retention(retention_rate);

COMMENT ON TABLE aggregates.cohort_retention IS 'Retention analysis by signup cohort';

-- ==============================================================================
-- aggregates.user_engagement_levels - MATERIALIZED VIEW
-- ==============================================================================
-- Purpose: Segment users by engagement intensity for targeting
-- Source: core.unified_users
-- Refresh: Daily
-- ==============================================================================

CREATE MATERIALIZED VIEW aggregates.user_engagement_levels AS
SELECT
    chemlink_id AS user_id,
    email,
    first_name,
    last_name,
    has_finder,
    
    -- Calculate engagement score (weighted)
    (posts_created * 3 + comments_made * 2 + votes_cast * 1 + collections_created * 5) AS engagement_score,
    
    -- Classify engagement level
    CASE
        WHEN (posts_created * 3 + comments_made * 2 + votes_cast * 1 + collections_created * 5) >= 50 THEN 'POWER_USER'
        WHEN (posts_created * 3 + comments_made * 2 + votes_cast * 1 + collections_created * 5) >= 20 THEN 'ACTIVE'
        WHEN (posts_created + comments_made + votes_cast + collections_created) > 0 THEN 'CASUAL'
        WHEN last_activity_date IS NOT NULL THEN 'LURKER'
        ELSE 'INACTIVE'
    END AS engagement_level,
    
    -- Activity counts
    posts_created,
    comments_made,
    votes_cast,
    collections_created,
    posts_created + comments_made + votes_cast + collections_created AS total_activities,
    
    -- Recency
    last_activity_date,
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - last_activity_date)) AS days_since_last_activity,
    
    -- User info
    signup_date,
    days_since_signup,
    user_lifecycle_stage,
    
    CURRENT_TIMESTAMP AS updated_at
FROM core.unified_users
WHERE deleted_at IS NULL
    AND is_test_account = FALSE;

CREATE UNIQUE INDEX idx_engagement_levels_user ON aggregates.user_engagement_levels(user_id);
CREATE INDEX idx_engagement_levels_level ON aggregates.user_engagement_levels(engagement_level);
CREATE INDEX idx_engagement_levels_score ON aggregates.user_engagement_levels(engagement_score DESC);

COMMENT ON MATERIALIZED VIEW aggregates.user_engagement_levels IS 'User segmentation by engagement intensity';

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'aggregates'
ORDER BY tablename;

-- Also check materialized views
SELECT 
    schemaname,
    matviewname AS tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) AS size
FROM pg_matviews
WHERE schemaname = 'aggregates'
ORDER BY matviewname;

-- Expected: 3 tables + 1 materialized view

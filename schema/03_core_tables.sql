-- ==============================================================================
-- ChemLink Analytics Database - Core Tables
-- ==============================================================================
-- Purpose: Cleaned, unified, and transformed data
-- Schema: core
-- Refresh Strategy: Nightly ETL
-- ==============================================================================

-- ==============================================================================
-- core.unified_users - MASTER USER TABLE
-- ==============================================================================
-- Purpose: Single source of truth combining ChemLink + Engagement data
-- Sources: staging.chemlink_persons + staging.engagement_persons + activity aggregations
-- ==============================================================================

CREATE TABLE core.unified_users (
    -- Primary identifiers
    chemlink_id BIGINT PRIMARY KEY,
    engagement_person_id BIGINT,
    person_id UUID,
    
    -- Basic profile
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    
    -- User type
    has_finder BOOLEAN DEFAULT FALSE,
    user_type VARCHAR(50), -- 'FINDER', 'STANDARD'
    
    -- Profile metrics (from ChemLink)
    experience_count INT DEFAULT 0,
    education_count INT DEFAULT 0,
    profile_completion_score INT DEFAULT 0, -- 0-100 calculated
    
    -- Engagement metrics (from Engagement Platform)
    posts_created INT DEFAULT 0,
    comments_made INT DEFAULT 0,
    votes_cast INT DEFAULT 0,
    collections_created INT DEFAULT 0,
    mentions_received INT DEFAULT 0,
    groups_joined INT DEFAULT 0,
    views_given INT DEFAULT 0,
    
    -- Calculated lifecycle fields
    signup_date TIMESTAMP,
    last_activity_date TIMESTAMP,
    first_post_date TIMESTAMP,
    first_vote_date TIMESTAMP,
    days_since_signup INT,
    days_to_first_activity INT,
    
    -- User lifecycle stage
    user_lifecycle_stage VARCHAR(50), -- NEW, ACTIVATED, ENGAGED, DORMANT, CHURNED
    activation_status BOOLEAN DEFAULT FALSE,
    activated_at TIMESTAMP,
    
    -- Data quality
    is_test_account BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE UNIQUE INDEX idx_unified_users_chemlink ON core.unified_users(chemlink_id);
CREATE INDEX idx_unified_users_engagement ON core.unified_users(engagement_person_id);
CREATE INDEX idx_unified_users_email ON core.unified_users(email);
CREATE INDEX idx_unified_users_has_finder ON core.unified_users(has_finder);
CREATE INDEX idx_unified_users_signup ON core.unified_users(signup_date);
CREATE INDEX idx_unified_users_lifecycle ON core.unified_users(user_lifecycle_stage);
CREATE INDEX idx_unified_users_activated ON core.unified_users(activation_status);
CREATE INDEX idx_unified_users_test ON core.unified_users(is_test_account);

COMMENT ON TABLE core.unified_users IS 'Master user table combining ChemLink and Engagement Platform data';

-- ==============================================================================
-- core.user_activity_events - UNIFIED EVENT STREAM
-- ==============================================================================
-- Purpose: All user actions from both databases in one timeline
-- Sources: All staging activity tables
-- ==============================================================================

CREATE TABLE core.user_activity_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL, -- FK to core.unified_users.chemlink_id
    activity_type VARCHAR(50) NOT NULL, -- post, comment, vote, collection, view, profile_update, etc.
    activity_date TIMESTAMP NOT NULL,
    
    -- Source tracking
    source_database VARCHAR(50), -- chemlink, engagement
    source_table VARCHAR(100),
    source_id BIGINT,
    
    -- Flexible metadata
    metadata JSONB, -- Store any additional context
    
    -- Calculated fields
    days_since_signup INT,
    is_first_activity_of_type BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_user_events_user ON core.user_activity_events(user_id);
CREATE INDEX idx_user_events_type ON core.user_activity_events(activity_type);
CREATE INDEX idx_user_events_date ON core.user_activity_events(activity_date);
CREATE INDEX idx_user_events_source ON core.user_activity_events(source_database, source_table);
CREATE INDEX idx_user_events_days_signup ON core.user_activity_events(days_since_signup);

COMMENT ON TABLE core.user_activity_events IS 'Unified event stream for all user activities across both databases';

-- ==============================================================================
-- core.user_cohorts - COHORT ANALYSIS
-- ==============================================================================
-- Purpose: Group users by signup month for retention analysis
-- Source: core.unified_users (aggregated)
-- ==============================================================================

CREATE TABLE core.user_cohorts (
    cohort_month DATE PRIMARY KEY,
    
    -- Cohort size
    total_users INT DEFAULT 0,
    finder_users INT DEFAULT 0,
    standard_users INT DEFAULT 0,
    
    -- Profile metrics averages
    avg_profile_completion DECIMAL(5,2) DEFAULT 0,
    avg_experience_count DECIMAL(5,2) DEFAULT 0,
    avg_education_count DECIMAL(5,2) DEFAULT 0,
    
    -- Activation metrics
    activated_users INT DEFAULT 0,
    activation_rate DECIMAL(5,2) DEFAULT 0,
    avg_days_to_activation DECIMAL(8,2),
    
    -- Retention metrics
    retained_30d INT DEFAULT 0,
    retained_60d INT DEFAULT 0,
    retained_90d INT DEFAULT 0,
    retention_rate_30d DECIMAL(5,2) DEFAULT 0,
    retention_rate_60d DECIMAL(5,2) DEFAULT 0,
    retention_rate_90d DECIMAL(5,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cohorts_month ON core.user_cohorts(cohort_month);
CREATE INDEX idx_cohorts_activation ON core.user_cohorts(activation_rate);

COMMENT ON TABLE core.user_cohorts IS 'Monthly cohort analysis for user retention and activation';

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'core'
ORDER BY tablename;

-- Expected: 3 tables (unified_users, user_activity_events, user_cohorts)

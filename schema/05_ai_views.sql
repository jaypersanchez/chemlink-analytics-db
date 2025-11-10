-- ==============================================================================
-- ChemLink Analytics Database - AI Training Data Views
-- ==============================================================================
-- Purpose: Feature-engineered datasets for Alchemi AI training
-- Schema: ai
-- Refresh Strategy: Monthly (for training runs)
-- ==============================================================================

-- ==============================================================================
-- ai.activation_training_data - ACTIVATION PREDICTION
-- ==============================================================================
-- Purpose: Features + labels for predicting which new users will activate
-- Use Case: Identify at-risk new signups, target onboarding efforts
-- Source: core.unified_users
-- ==============================================================================

CREATE MATERIALIZED VIEW ai.activation_training_data AS
SELECT
    chemlink_id AS user_id,
    
    -- FEATURES (X) - What we know at signup
    has_finder,
    experience_count,
    education_count,
    profile_completion_score,
    EXTRACT(DOW FROM signup_date) AS signup_day_of_week, -- 0=Sunday, 6=Saturday
    EXTRACT(HOUR FROM signup_date) AS signup_hour,
    EXTRACT(MONTH FROM signup_date) AS signup_month,
    
    -- Early behavior signals (first 7 days)
    CASE WHEN days_to_first_activity <= 7 THEN days_to_first_activity ELSE NULL END AS days_to_first_activity_7d,
    CASE WHEN days_to_first_activity <= 1 THEN TRUE ELSE FALSE END AS activated_within_24h,
    
    -- LABELS (Y) - What we want to predict
    activation_status AS activated,
    CASE WHEN posts_created > 0 OR comments_made > 0 THEN TRUE ELSE FALSE END AS activated_social,
    CASE WHEN votes_cast > 0 OR collections_created > 0 THEN TRUE ELSE FALSE END AS activated_finder,
    CASE WHEN (posts_created + comments_made + votes_cast + collections_created) >= 3 THEN TRUE ELSE FALSE END AS became_engaged,
    
    -- Days to activation (for those who activated)
    days_to_first_activity,
    
    -- Metadata
    DATE_TRUNC('month', signup_date) AS cohort_month,
    signup_date,
    created_at,
    
    CURRENT_TIMESTAMP AS generated_at
FROM core.unified_users
WHERE deleted_at IS NULL
    AND is_test_account = FALSE
    AND signup_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months') -- Last 12 months only
ORDER BY signup_date DESC;

CREATE UNIQUE INDEX idx_activation_training_user ON ai.activation_training_data(user_id);
CREATE INDEX idx_activation_training_cohort ON ai.activation_training_data(cohort_month);
CREATE INDEX idx_activation_training_label ON ai.activation_training_data(activated);

COMMENT ON MATERIALIZED VIEW ai.activation_training_data IS 'Training dataset for predicting user activation';

-- ==============================================================================
-- ai.engagement_training_data - ENGAGEMENT PREDICTION
-- ==============================================================================
-- Purpose: Features + labels for predicting engagement level after 90 days
-- Use Case: Predict power users, identify churn risk
-- Source: core.unified_users + aggregates.user_engagement_levels
-- ==============================================================================

CREATE MATERIALIZED VIEW ai.engagement_training_data AS
SELECT
    u.chemlink_id AS user_id,
    
    -- FEATURES (X) - Profile and early signals
    u.has_finder,
    u.profile_completion_score,
    u.experience_count,
    u.education_count,
    u.days_since_signup,
    
    -- Early activity signals (first 30 days)
    (SELECT COUNT(*) FROM core.user_activity_events e 
     WHERE e.user_id = u.chemlink_id 
     AND e.days_since_signup <= 30) AS first_30d_activities,
    
    (SELECT COUNT(DISTINCT activity_type) FROM core.user_activity_events e 
     WHERE e.user_id = u.chemlink_id 
     AND e.days_since_signup <= 30) AS first_30d_activity_types,
    
    -- Profile behavior
    CASE WHEN u.profile_completion_score >= 50 THEN TRUE ELSE FALSE END AS completed_profile,
    CASE WHEN u.experience_count > 0 THEN TRUE ELSE FALSE END AS added_experience,
    CASE WHEN u.education_count > 0 THEN TRUE ELSE FALSE END AS added_education,
    
    -- LABELS (Y) - Outcomes after 90 days
    CASE WHEN el.engagement_level IN ('POWER_USER', 'ACTIVE') THEN TRUE ELSE FALSE END AS became_power_user,
    COALESCE(el.engagement_score, 0) AS engagement_score_90d,
    CASE WHEN u.last_activity_date >= u.signup_date + INTERVAL '90 days' THEN TRUE ELSE FALSE END AS retained_90d,
    CASE WHEN u.user_lifecycle_stage = 'CHURNED' THEN TRUE ELSE FALSE END AS churned,
    
    -- Current engagement level (categorical label)
    COALESCE(el.engagement_level, 'INACTIVE') AS final_engagement_level,
    
    -- Metadata
    DATE_TRUNC('month', u.signup_date) AS cohort_month,
    u.signup_date,
    u.last_activity_date,
    
    CURRENT_TIMESTAMP AS generated_at
FROM core.unified_users u
LEFT JOIN aggregates.user_engagement_levels el ON u.chemlink_id = el.user_id
WHERE u.deleted_at IS NULL
    AND u.is_test_account = FALSE
    AND u.days_since_signup >= 90 -- Only users with 90+ days of data
    AND u.signup_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
ORDER BY u.signup_date DESC;

CREATE UNIQUE INDEX idx_engagement_training_user ON ai.engagement_training_data(user_id);
CREATE INDEX idx_engagement_training_cohort ON ai.engagement_training_data(cohort_month);
CREATE INDEX idx_engagement_training_label ON ai.engagement_training_data(became_power_user);
CREATE INDEX idx_engagement_training_level ON ai.engagement_training_data(final_engagement_level);

COMMENT ON MATERIALIZED VIEW ai.engagement_training_data IS 'Training dataset for predicting long-term engagement';

-- ==============================================================================
-- HELPER FUNCTIONS FOR AI DATA EXPORT
-- ==============================================================================

-- Function to export activation training data as CSV
CREATE OR REPLACE FUNCTION ai.export_activation_training_csv()
RETURNS TEXT AS $$
BEGIN
    EXECUTE format('
        COPY (
            SELECT 
                user_id,
                has_finder::int,
                experience_count,
                education_count,
                profile_completion_score,
                signup_day_of_week,
                signup_hour,
                signup_month,
                days_to_first_activity_7d,
                activated_within_24h::int,
                activated::int,
                activated_social::int,
                activated_finder::int,
                became_engaged::int
            FROM ai.activation_training_data
            WHERE cohort_month >= DATE_TRUNC(''month'', CURRENT_DATE - INTERVAL ''6 months'')
        ) TO ''/tmp/activation_training_data_%s.csv'' CSV HEADER
    ', TO_CHAR(CURRENT_DATE, 'YYYYMMDD'));
    
    RETURN 'Exported to /tmp/activation_training_data_' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '.csv';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ai.export_activation_training_csv() IS 'Export activation training data to CSV file';

-- Function to export engagement training data as CSV
CREATE OR REPLACE FUNCTION ai.export_engagement_training_csv()
RETURNS TEXT AS $$
BEGIN
    EXECUTE format('
        COPY (
            SELECT 
                user_id,
                has_finder::int,
                profile_completion_score,
                experience_count,
                education_count,
                days_since_signup,
                first_30d_activities,
                first_30d_activity_types,
                completed_profile::int,
                added_experience::int,
                added_education::int,
                became_power_user::int,
                engagement_score_90d,
                retained_90d::int,
                churned::int,
                final_engagement_level
            FROM ai.engagement_training_data
            WHERE cohort_month >= DATE_TRUNC(''month'', CURRENT_DATE - INTERVAL ''6 months'')
        ) TO ''/tmp/engagement_training_data_%s.csv'' CSV HEADER
    ', TO_CHAR(CURRENT_DATE, 'YYYYMMDD'));
    
    RETURN 'Exported to /tmp/engagement_training_data_' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '.csv';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ai.export_engagement_training_csv() IS 'Export engagement training data to CSV file';

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

SELECT 
    schemaname,
    matviewname AS tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) AS size
FROM pg_matviews
WHERE schemaname = 'ai'
ORDER BY matviewname;

-- Expected: 2 materialized views

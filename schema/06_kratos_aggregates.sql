-- ==============================================================================
-- KRATOS AUTHENTICATION & SESSION ANALYTICS AGGREGATES
-- ==============================================================================
-- Purpose: Pre-computed analytics for authentication, sessions, MFA adoption,
--          device tracking, security monitoring, and user activation
-- Source: staging.kratos_* tables
-- Target: aggregates schema
-- ==============================================================================

-- ==============================================================================
-- 1. DAILY LOGIN ACTIVITY METRICS
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_daily_logins CASCADE;

CREATE TABLE aggregates.kratos_daily_logins AS
SELECT 
    DATE(authenticated_at) as metric_date,
    -- Login volume
    COUNT(DISTINCT identity_id) as unique_users_logged_in,
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE active = true) as active_sessions,
    COUNT(*) FILTER (WHERE logout_at IS NOT NULL) as logged_out_sessions,
    
    -- Authentication levels
    COUNT(*) FILTER (WHERE aal = 'aal2') as mfa_sessions,
    COUNT(*) FILTER (WHERE aal = 'aal1') as password_only_sessions,
    ROUND(100.0 * COUNT(*) FILTER (WHERE aal = 'aal2') / NULLIF(COUNT(*), 0), 2) as mfa_session_rate,
    
    -- Session metrics
    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/60)::numeric, 2) as avg_session_minutes,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/60)::numeric, 2) as median_session_minutes,
    
    -- Device tracking
    COUNT(DISTINCT ip_address) as unique_ips,
    COUNT(DISTINCT CASE WHEN user_agent LIKE '%Mobile%' THEN identity_id END) as mobile_users,
    COUNT(DISTINCT CASE WHEN user_agent NOT LIKE '%Mobile%' AND user_agent NOT LIKE '%Tablet%' THEN identity_id END) as desktop_users
    
FROM staging.kratos_sessions
WHERE authenticated_at IS NOT NULL
GROUP BY DATE(authenticated_at);

CREATE INDEX idx_kratos_daily_date ON aggregates.kratos_daily_logins(metric_date DESC);

COMMENT ON TABLE aggregates.kratos_daily_logins IS 'Daily authentication activity metrics including MFA usage and session stats';

-- ==============================================================================
-- 2. USER ACTIVITY SEGMENTATION
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_user_activity CASCADE;

CREATE TABLE aggregates.kratos_user_activity AS
SELECT 
    identity_id,
    
    -- Session metrics
    COUNT(*) as total_sessions,
    COUNT(DISTINCT DATE(authenticated_at)) as days_active,
    MIN(authenticated_at) as first_login,
    MAX(authenticated_at) as last_login,
    
    -- Recency (days since last login)
    CURRENT_DATE - DATE(MAX(authenticated_at)) as days_since_last_login,
    
    -- Activity segmentation
    CASE 
        WHEN MAX(authenticated_at) >= CURRENT_DATE - INTERVAL '7 days' THEN 'Active (< 7 days)'
        WHEN MAX(authenticated_at) >= CURRENT_DATE - INTERVAL '30 days' THEN 'Recent (7-30 days)'
        WHEN MAX(authenticated_at) >= CURRENT_DATE - INTERVAL '90 days' THEN 'At Risk (30-90 days)'
        ELSE 'Dormant (> 90 days)'
    END as recency_segment,
    
    -- Login frequency
    CASE 
        WHEN COUNT(DISTINCT DATE(authenticated_at)) >= 20 THEN 'Daily Active'
        WHEN COUNT(DISTINCT DATE(authenticated_at)) >= 10 THEN 'Weekly Active'
        WHEN COUNT(DISTINCT DATE(authenticated_at)) >= 4 THEN 'Bi-Weekly Active'
        ELSE 'Occasional'
    END as frequency_segment,
    
    -- Security metrics
    COUNT(DISTINCT ip_address) as unique_ips,
    MAX(aal) as highest_aal,
    COUNT(*) FILTER (WHERE aal = 'aal2') as mfa_session_count,
    
    -- Session duration
    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/3600)::numeric, 2) as avg_session_hours,
    
    -- Risk indicators
    CASE 
        WHEN COUNT(DISTINCT ip_address) > 10 THEN 'High IP Diversity'
        WHEN COUNT(DISTINCT ip_address) > 5 THEN 'Moderate IP Diversity'
        ELSE 'Normal'
    END as ip_risk_level
    
FROM staging.kratos_sessions
WHERE authenticated_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY identity_id;

CREATE INDEX idx_kratos_user_identity ON aggregates.kratos_user_activity(identity_id);
CREATE INDEX idx_kratos_user_recency ON aggregates.kratos_user_activity(recency_segment);
CREATE INDEX idx_kratos_user_frequency ON aggregates.kratos_user_activity(frequency_segment);
CREATE INDEX idx_kratos_user_last_login ON aggregates.kratos_user_activity(last_login DESC);

COMMENT ON TABLE aggregates.kratos_user_activity IS 'Per-user activity patterns including recency, frequency, and risk indicators';

-- ==============================================================================
-- 3. MFA ADOPTION ANALYTICS
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_mfa_adoption CASCADE;

CREATE TABLE aggregates.kratos_mfa_adoption AS
SELECT 
    DATE_TRUNC('month', created_at) as metric_month,
    
    -- Credential type distribution
    COUNT(DISTINCT identity_id) FILTER (WHERE type = 'totp') as totp_users,
    COUNT(DISTINCT identity_id) FILTER (WHERE type = 'webauthn') as webauthn_users,
    COUNT(DISTINCT identity_id) FILTER (WHERE type = 'password') as password_only_users,
    
    -- Total counts
    COUNT(DISTINCT identity_id) as total_users_with_credentials,
    COUNT(*) as total_credentials,
    
    -- Adoption rates
    ROUND(100.0 * COUNT(DISTINCT identity_id) FILTER (WHERE type IN ('totp', 'webauthn')) / 
          NULLIF(COUNT(DISTINCT identity_id), 0), 2) as mfa_adoption_rate
    
FROM staging.kratos_identity_credentials
GROUP BY DATE_TRUNC('month', created_at);

CREATE INDEX idx_kratos_mfa_month ON aggregates.kratos_mfa_adoption(metric_month DESC);

COMMENT ON TABLE aggregates.kratos_mfa_adoption IS 'Monthly MFA adoption trends by credential type';

-- ==============================================================================
-- 4. DEVICE & LOCATION ANALYTICS
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_device_analytics CASCADE;

CREATE TABLE aggregates.kratos_device_analytics AS
SELECT 
    DATE(authenticated_at) as metric_date,
    
    -- Device type classification
    CASE 
        WHEN user_agent LIKE '%Mobile%' THEN 'Mobile'
        WHEN user_agent LIKE '%Tablet%' THEN 'Tablet'
        WHEN user_agent LIKE '%Desktop%' OR user_agent LIKE '%Windows%' OR user_agent LIKE '%Macintosh%' THEN 'Desktop'
        ELSE 'Unknown'
    END as device_type,
    
    -- Browser detection (basic)
    CASE 
        WHEN user_agent LIKE '%Chrome%' THEN 'Chrome'
        WHEN user_agent LIKE '%Safari%' THEN 'Safari'
        WHEN user_agent LIKE '%Firefox%' THEN 'Firefox'
        WHEN user_agent LIKE '%Edge%' THEN 'Edge'
        ELSE 'Other'
    END as browser_type,
    
    -- Session metrics by device
    COUNT(DISTINCT identity_id) as unique_users,
    COUNT(*) as session_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/60)::numeric, 2) as avg_session_minutes
    
FROM staging.kratos_sessions
WHERE authenticated_at >= CURRENT_DATE - INTERVAL '90 days'
  AND user_agent IS NOT NULL
GROUP BY 
    DATE(authenticated_at),
    CASE 
        WHEN user_agent LIKE '%Mobile%' THEN 'Mobile'
        WHEN user_agent LIKE '%Tablet%' THEN 'Tablet'
        WHEN user_agent LIKE '%Desktop%' OR user_agent LIKE '%Windows%' OR user_agent LIKE '%Macintosh%' THEN 'Desktop'
        ELSE 'Unknown'
    END,
    CASE 
        WHEN user_agent LIKE '%Chrome%' THEN 'Chrome'
        WHEN user_agent LIKE '%Safari%' THEN 'Safari'
        WHEN user_agent LIKE '%Firefox%' THEN 'Firefox'
        WHEN user_agent LIKE '%Edge%' THEN 'Edge'
        ELSE 'Other'
    END;

CREATE INDEX idx_kratos_device_date ON aggregates.kratos_device_analytics(metric_date DESC);
CREATE INDEX idx_kratos_device_type ON aggregates.kratos_device_analytics(device_type);

COMMENT ON TABLE aggregates.kratos_device_analytics IS 'Device and browser usage patterns by date';

-- ==============================================================================
-- 5. SESSION DURATION & FREQUENCY METRICS
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_session_metrics CASCADE;

CREATE TABLE aggregates.kratos_session_metrics AS
SELECT 
    identity_id,
    DATE(authenticated_at) as session_date,
    
    -- Daily session stats per user
    COUNT(*) as sessions_per_day,
    
    -- Session duration metrics
    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/60)::numeric, 2) as avg_session_minutes,
    ROUND(MIN(EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/60)::numeric, 2) as min_session_minutes,
    ROUND(MAX(EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/60)::numeric, 2) as max_session_minutes,
    
    -- Active sessions
    COUNT(*) FILTER (WHERE active = true) as active_sessions,
    COUNT(*) FILTER (WHERE logout_at IS NOT NULL) as explicit_logouts,
    
    -- Time patterns
    ARRAY_AGG(DISTINCT EXTRACT(HOUR FROM authenticated_at)::int ORDER BY EXTRACT(HOUR FROM authenticated_at)::int) as login_hours
    
FROM staging.kratos_sessions
WHERE authenticated_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY identity_id, DATE(authenticated_at);

CREATE INDEX idx_kratos_session_identity_date ON aggregates.kratos_session_metrics(identity_id, session_date DESC);
CREATE INDEX idx_kratos_session_date ON aggregates.kratos_session_metrics(session_date DESC);

COMMENT ON TABLE aggregates.kratos_session_metrics IS 'Detailed per-user daily session patterns and duration metrics';

-- ==============================================================================
-- 6. ACCOUNT STATE DISTRIBUTION
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_account_states CASCADE;

CREATE TABLE aggregates.kratos_account_states AS
SELECT 
    state,
    COUNT(*) as identity_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage,
    
    -- Additional metrics
    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') as new_in_last_30_days,
    MIN(created_at) as oldest_account,
    MAX(created_at) as newest_account
    
FROM staging.kratos_identities
WHERE deleted_at IS NULL
GROUP BY state;

COMMENT ON TABLE aggregates.kratos_account_states IS 'Distribution of account states (active, inactive, etc.)';

-- ==============================================================================
-- 7. ACTIVATION FUNNEL (SIGNUP TO FIRST LOGIN)
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_activation_funnel CASCADE;

CREATE TABLE aggregates.kratos_activation_funnel AS
SELECT 
    DATE_TRUNC('week', ki.created_at) as signup_week,
    
    -- Cohort size
    COUNT(*) as new_identities,
    
    -- Activation windows
    COUNT(CASE WHEN s.first_login <= ki.created_at + INTERVAL '1 day' THEN 1 END) as activated_within_1_day,
    COUNT(CASE WHEN s.first_login <= ki.created_at + INTERVAL '7 days' THEN 1 END) as activated_within_7_days,
    COUNT(CASE WHEN s.first_login <= ki.created_at + INTERVAL '30 days' THEN 1 END) as activated_within_30_days,
    COUNT(CASE WHEN s.first_login IS NOT NULL THEN 1 END) as ever_activated,
    
    -- Activation rates
    ROUND(100.0 * COUNT(CASE WHEN s.first_login <= ki.created_at + INTERVAL '1 day' THEN 1 END) / COUNT(*), 2) as day1_activation_rate,
    ROUND(100.0 * COUNT(CASE WHEN s.first_login <= ki.created_at + INTERVAL '7 days' THEN 1 END) / COUNT(*), 2) as week1_activation_rate,
    ROUND(100.0 * COUNT(CASE WHEN s.first_login <= ki.created_at + INTERVAL '30 days' THEN 1 END) / COUNT(*), 2) as month1_activation_rate,
    
    -- Time to first login (average for those who activated)
    ROUND(AVG(EXTRACT(EPOCH FROM (s.first_login - ki.created_at))/3600) 
          FILTER (WHERE s.first_login IS NOT NULL)::numeric, 2) as avg_hours_to_first_login
    
FROM staging.kratos_identities ki
LEFT JOIN (
    SELECT 
        identity_id, 
        MIN(authenticated_at) as first_login
    FROM staging.kratos_sessions
    GROUP BY identity_id
) s ON ki.id = s.identity_id
WHERE ki.created_at >= CURRENT_DATE - INTERVAL '180 days'
  AND ki.deleted_at IS NULL
GROUP BY DATE_TRUNC('week', ki.created_at);

CREATE INDEX idx_kratos_activation_week ON aggregates.kratos_activation_funnel(signup_week DESC);

COMMENT ON TABLE aggregates.kratos_activation_funnel IS 'Weekly cohort activation rates from signup to first login';

-- ==============================================================================
-- 8. SECURITY ANOMALY DETECTION VIEW
-- ==============================================================================

DROP VIEW IF EXISTS aggregates.kratos_security_alerts CASCADE;

CREATE VIEW aggregates.kratos_security_alerts AS
WITH user_session_stats AS (
    SELECT 
        identity_id,
        COUNT(*) as session_count_7d,
        COUNT(DISTINCT ip_address) as unique_ips_7d,
        COUNT(DISTINCT DATE(authenticated_at)) as active_days_7d,
        MAX(authenticated_at) as last_session
    FROM staging.kratos_sessions
    WHERE authenticated_at >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY identity_id
)
SELECT 
    identity_id,
    session_count_7d,
    unique_ips_7d,
    active_days_7d,
    last_session,
    
    -- Risk scoring
    CASE 
        WHEN unique_ips_7d > 10 THEN 'CRITICAL - Multiple IPs'
        WHEN session_count_7d > 100 THEN 'HIGH - Excessive Sessions'
        WHEN unique_ips_7d > 5 THEN 'MEDIUM - Multiple Locations'
        WHEN session_count_7d > 50 THEN 'MEDIUM - High Activity'
        ELSE 'LOW'
    END as risk_level,
    
    -- Anomaly flags
    unique_ips_7d > 5 as flag_multiple_ips,
    session_count_7d > 50 as flag_high_volume,
    (session_count_7d::float / NULLIF(active_days_7d, 0)) > 20 as flag_burst_activity
    
FROM user_session_stats
WHERE unique_ips_7d > 5 OR session_count_7d > 50
ORDER BY 
    CASE 
        WHEN unique_ips_7d > 10 THEN 1
        WHEN session_count_7d > 100 THEN 2
        WHEN unique_ips_7d > 5 THEN 3
        ELSE 4
    END,
    unique_ips_7d DESC,
    session_count_7d DESC;

COMMENT ON VIEW aggregates.kratos_security_alerts IS 'Real-time security anomaly detection for suspicious login patterns';

-- ==============================================================================
-- 9. LOGIN FREQUENCY SEGMENTATION
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_login_frequency_segments CASCADE;

CREATE TABLE aggregates.kratos_login_frequency_segments AS
WITH login_frequency AS (
    SELECT 
        identity_id,
        COUNT(*) as login_count,
        COUNT(DISTINCT DATE(authenticated_at)) as days_active,
        MIN(authenticated_at) as first_login,
        MAX(authenticated_at) as last_login
    FROM staging.kratos_sessions
    WHERE authenticated_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY identity_id
)
SELECT 
    CASE 
        WHEN days_active >= 25 THEN 'Daily Active (25+ days)'
        WHEN days_active >= 15 THEN 'Highly Active (15-24 days)'
        WHEN days_active >= 8 THEN 'Weekly Active (8-14 days)'
        WHEN days_active >= 4 THEN 'Bi-Weekly Active (4-7 days)'
        ELSE 'Occasional (< 4 days)'
    END as frequency_segment,
    
    COUNT(*) as user_count,
    ROUND(AVG(login_count)::numeric, 2) as avg_logins,
    ROUND(AVG(days_active)::numeric, 2) as avg_days_active,
    ROUND(AVG(login_count::float / NULLIF(days_active, 0))::numeric, 2) as avg_logins_per_active_day,
    
    -- Percentiles
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY login_count) as p25_logins,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY login_count) as median_logins,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY login_count) as p75_logins
    
FROM login_frequency
GROUP BY frequency_segment;

COMMENT ON TABLE aggregates.kratos_login_frequency_segments IS 'User segmentation by login frequency in last 30 days';

-- ==============================================================================
-- 10. HOURLY LOGIN PATTERNS
-- ==============================================================================

DROP TABLE IF EXISTS aggregates.kratos_hourly_patterns CASCADE;

CREATE TABLE aggregates.kratos_hourly_patterns AS
SELECT 
    EXTRACT(HOUR FROM authenticated_at)::int as hour_of_day,
    EXTRACT(DOW FROM authenticated_at)::int as day_of_week, -- 0=Sunday, 6=Saturday
    
    COUNT(*) as total_sessions,
    COUNT(DISTINCT identity_id) as unique_users,
    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(seen_at, expires_at) - authenticated_at))/60)::numeric, 2) as avg_session_minutes,
    
    -- Weekday classification
    CASE 
        WHEN EXTRACT(DOW FROM authenticated_at) IN (0, 6) THEN 'Weekend'
        ELSE 'Weekday'
    END as day_type
    
FROM staging.kratos_sessions
WHERE authenticated_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY 
    EXTRACT(HOUR FROM authenticated_at)::int,
    EXTRACT(DOW FROM authenticated_at)::int,
    CASE 
        WHEN EXTRACT(DOW FROM authenticated_at) IN (0, 6) THEN 'Weekend'
        ELSE 'Weekday'
    END;

CREATE INDEX idx_kratos_hourly_hour ON aggregates.kratos_hourly_patterns(hour_of_day);
CREATE INDEX idx_kratos_hourly_dow ON aggregates.kratos_hourly_patterns(day_of_week);

COMMENT ON TABLE aggregates.kratos_hourly_patterns IS 'Login patterns by hour of day and day of week';

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('aggregates.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'aggregates'
  AND tablename LIKE 'kratos_%'
ORDER BY tablename;

-- ==============================================================================
-- SUMMARY
-- ==============================================================================
-- Tables created:
-- 1. kratos_daily_logins - Daily login volume and MFA metrics
-- 2. kratos_user_activity - Per-user activity segmentation
-- 3. kratos_mfa_adoption - Monthly MFA adoption trends
-- 4. kratos_device_analytics - Device and browser usage
-- 5. kratos_session_metrics - Detailed session duration patterns
-- 6. kratos_account_states - Account state distribution
-- 7. kratos_activation_funnel - Signup to first login conversion
-- 8. kratos_security_alerts (VIEW) - Real-time anomaly detection
-- 9. kratos_login_frequency_segments - 30-day login frequency cohorts
-- 10. kratos_hourly_patterns - Time-of-day usage patterns
-- ==============================================================================

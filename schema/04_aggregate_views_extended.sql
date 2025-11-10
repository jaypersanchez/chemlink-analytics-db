-- ==============================================================================
-- Extended Aggregates for Complete Dashboard Coverage
-- ==============================================================================

-- ==============================================================================
-- aggregates.post_metrics - POST ENGAGEMENT ANALYTICS
-- ==============================================================================
CREATE TABLE aggregates.post_metrics (
    metric_date DATE PRIMARY KEY,
    
    -- Post frequency
    posts_created INT DEFAULT 0,
    comments_created INT DEFAULT 0,
    unique_posters INT DEFAULT 0,
    unique_commenters INT DEFAULT 0,
    
    -- Engagement rates
    avg_posts_per_poster DECIMAL(5,2) DEFAULT 0,
    avg_comments_per_post DECIMAL(5,2) DEFAULT 0,
    avg_votes_per_post DECIMAL(5,2) DEFAULT 0,
    engagement_rate_comments_pct DECIMAL(5,2) DEFAULT 0, -- comments per post %
    engagement_rate_votes_pct DECIMAL(5,2) DEFAULT 0, -- votes per post %
    total_votes INT DEFAULT 0
    
    -- Content type breakdown
    text_posts INT DEFAULT 0,
    link_posts INT DEFAULT 0,
    media_posts INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_post_metrics_date ON aggregates.post_metrics(metric_date);

-- ==============================================================================
-- aggregates.finder_metrics - FINDER SEARCH ANALYTICS
-- ==============================================================================
CREATE TABLE aggregates.finder_metrics (
    metric_date DATE PRIMARY KEY,
    
    -- Search activity
    total_searches INT DEFAULT 0,
    unique_searchers INT DEFAULT 0,
    avg_searches_per_user DECIMAL(5,2) DEFAULT 0,
    
    -- Vote activity
    total_votes INT DEFAULT 0,
    unique_voters INT DEFAULT 0,
    upvotes INT DEFAULT 0,
    downvotes INT DEFAULT 0,
    
    -- Engagement
    profiles_viewed INT DEFAULT 0,
    unique_profile_viewers INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_finder_metrics_date ON aggregates.finder_metrics(metric_date);

-- ==============================================================================
-- aggregates.collection_metrics - COLLECTION ANALYTICS
-- ==============================================================================
CREATE TABLE aggregates.collection_metrics (
    metric_date DATE PRIMARY KEY,
    
    -- Collections created
    total_collections_created INT DEFAULT 0,
    public_collections INT DEFAULT 0,
    private_collections INT DEFAULT 0,
    unique_collectors INT DEFAULT 0,
    
    -- Collection activity
    profiles_added_to_collections INT DEFAULT 0,
    avg_profiles_per_collection DECIMAL(5,2) DEFAULT 0,
    
    -- Sharing (placeholder - need sharing data)
    collections_shared INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_collection_metrics_date ON aggregates.collection_metrics(metric_date);

-- ==============================================================================
-- aggregates.profile_metrics - PROFILE UPDATE ANALYTICS
-- ==============================================================================
CREATE TABLE aggregates.profile_metrics (
    metric_date DATE PRIMARY KEY,
    
    -- Profile updates
    profiles_updated INT DEFAULT 0,
    experiences_added INT DEFAULT 0,
    education_added INT DEFAULT 0,
    
    -- Profile completeness (snapshot)
    avg_profile_completion_score DECIMAL(5,2) DEFAULT 0,
    profiles_with_headline INT DEFAULT 0,
    profiles_with_linkedin INT DEFAULT 0,
    profiles_with_location INT DEFAULT 0,
    profiles_with_experience INT DEFAULT 0,
    profiles_with_education INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_profile_metrics_date ON aggregates.profile_metrics(metric_date);

-- ==============================================================================
-- aggregates.funnel_metrics - ACCOUNT CREATION FUNNEL
-- ==============================================================================
CREATE TABLE aggregates.funnel_metrics (
    metric_date DATE PRIMARY KEY,
    
    -- Funnel stages (cumulative counts)
    total_signups INT DEFAULT 0,
    profiles_with_basic_info INT DEFAULT 0,
    profiles_with_experience INT DEFAULT 0,
    profiles_with_education INT DEFAULT 0,
    profiles_completed INT DEFAULT 0,
    profiles_activated INT DEFAULT 0,
    
    -- Conversion rates
    basic_info_rate DECIMAL(5,2) DEFAULT 0,
    experience_rate DECIMAL(5,2) DEFAULT 0,
    education_rate DECIMAL(5,2) DEFAULT 0,
    completion_rate DECIMAL(5,2) DEFAULT 0,
    activation_rate DECIMAL(5,2) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_funnel_metrics_date ON aggregates.funnel_metrics(metric_date);

COMMENT ON TABLE aggregates.post_metrics IS 'Daily post and comment engagement metrics';
COMMENT ON TABLE aggregates.finder_metrics IS 'Daily finder search and vote analytics';
COMMENT ON TABLE aggregates.collection_metrics IS 'Daily collection creation and usage metrics';
COMMENT ON TABLE aggregates.profile_metrics IS 'Daily profile update and completion metrics';
COMMENT ON TABLE aggregates.funnel_metrics IS 'Daily account creation funnel conversion metrics';

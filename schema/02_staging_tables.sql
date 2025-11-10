-- ==============================================================================
-- ChemLink Analytics Database - Staging Tables
-- ==============================================================================
-- Purpose: Raw copies from production databases
-- Schema: staging
-- Sync Strategy: Daily ETL
-- ==============================================================================

-- ==============================================================================
-- CHEMLINK SERVICE STAGING TABLES
-- ==============================================================================

-- staging.chemlink_persons
-- Source: chemlink-service-prd.persons
CREATE TABLE staging.chemlink_persons (
    id BIGINT PRIMARY KEY,
    person_id UUID,
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    headline_description TEXT,
    linked_in_url VARCHAR(500),
    career_goals TEXT,
    business_experience_summary TEXT,
    location_id BIGINT,
    company_id BIGINT,
    role_id BIGINT,
    has_finder BOOLEAN DEFAULT FALSE,
    profile_picture_key VARCHAR(500),
    profile_pic_updated_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    -- ETL metadata
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_persons_email ON staging.chemlink_persons(email);
CREATE INDEX idx_chemlink_persons_created ON staging.chemlink_persons(created_at);
CREATE INDEX idx_chemlink_persons_has_finder ON staging.chemlink_persons(has_finder);
CREATE INDEX idx_chemlink_persons_deleted ON staging.chemlink_persons(deleted_at);

COMMENT ON TABLE staging.chemlink_persons IS 'User profiles from ChemLink Service (Profile Builder)';

-- staging.chemlink_experiences
-- Source: chemlink-service-prd.experiences
CREATE TABLE staging.chemlink_experiences (
    id BIGINT PRIMARY KEY,
    person_id BIGINT,
    company_id BIGINT,
    role_id BIGINT,
    project_id BIGINT,
    location_id BIGINT,
    description TEXT,
    start_date DATE,
    end_date DATE,
    type VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_exp_person ON staging.chemlink_experiences(person_id);
CREATE INDEX idx_chemlink_exp_created ON staging.chemlink_experiences(created_at);
CREATE INDEX idx_chemlink_exp_deleted ON staging.chemlink_experiences(deleted_at);

COMMENT ON TABLE staging.chemlink_experiences IS 'Work experience history';

-- staging.chemlink_education
-- Source: chemlink-service-prd.education
CREATE TABLE staging.chemlink_education (
    id BIGINT PRIMARY KEY,
    person_id BIGINT,
    school_id BIGINT,
    degree_id BIGINT,
    field_of_study VARCHAR(255),
    description TEXT,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_edu_person ON staging.chemlink_education(person_id);
CREATE INDEX idx_chemlink_edu_deleted ON staging.chemlink_education(deleted_at);

COMMENT ON TABLE staging.chemlink_education IS 'Educational background';

-- staging.chemlink_collections
-- Source: chemlink-service-prd.collections
CREATE TABLE staging.chemlink_collections (
    id BIGINT PRIMARY KEY,
    person_id BIGINT,
    name VARCHAR(255),
    description TEXT,
    privacy VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_coll_person ON staging.chemlink_collections(person_id);
CREATE INDEX idx_chemlink_coll_created ON staging.chemlink_collections(created_at);
CREATE INDEX idx_chemlink_coll_deleted ON staging.chemlink_collections(deleted_at);

COMMENT ON TABLE staging.chemlink_collections IS 'User-created expert collections (Finder feature)';

-- staging.chemlink_query_votes
-- Source: chemlink-service-prd.query_votes
-- NOTE: Uses voter_id not person_id, has NO deleted_at column
CREATE TABLE staging.chemlink_query_votes (
    id BIGINT PRIMARY KEY,
    voter_id BIGINT,  -- Maps to persons.id
    query_embedding_id BIGINT,
    vote VARCHAR(50),
    created_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_votes_voter ON staging.chemlink_query_votes(voter_id);
CREATE INDEX idx_chemlink_votes_created ON staging.chemlink_query_votes(created_at);

COMMENT ON TABLE staging.chemlink_query_votes IS 'Search query voting activity (Finder feature)';

-- staging.chemlink_view_access
-- Source: chemlink-service-prd.view_access
CREATE TABLE staging.chemlink_view_access (
    id BIGINT PRIMARY KEY,
    person_id BIGINT,
    viewed_person_id BIGINT,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_view_person ON staging.chemlink_view_access(person_id);
CREATE INDEX idx_chemlink_view_created ON staging.chemlink_view_access(created_at);
CREATE INDEX idx_chemlink_view_deleted ON staging.chemlink_view_access(deleted_at);

COMMENT ON TABLE staging.chemlink_view_access IS 'Profile view activity tracking';

-- ==============================================================================
-- ENGAGEMENT PLATFORM STAGING TABLES
-- ==============================================================================

-- staging.engagement_persons
-- Source: engagement-platform-prd.persons
-- NOTE: external_id links to chemlink_persons.id
CREATE TABLE staging.engagement_persons (
    id BIGINT PRIMARY KEY,
    external_id BIGINT,  -- FK to staging.chemlink_persons.id
    iam_id VARCHAR(255),
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company_name VARCHAR(255),
    role_title VARCHAR(255),
    employment_status VARCHAR(100),
    mobile_number VARCHAR(50),
    mobile_number_country_code VARCHAR(10),
    profile_picture_key VARCHAR(500),
    profile_pic_updated_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_persons_external ON staging.engagement_persons(external_id);
CREATE INDEX idx_engagement_persons_email ON staging.engagement_persons(email);
CREATE INDEX idx_engagement_persons_created ON staging.engagement_persons(created_at);
CREATE INDEX idx_engagement_persons_deleted ON staging.engagement_persons(deleted_at);

COMMENT ON TABLE staging.engagement_persons IS 'Social platform profiles (links to ChemLink via external_id)';

-- staging.engagement_posts
-- Source: engagement-platform-prd.posts
CREATE TABLE staging.engagement_posts (
    id BIGINT PRIMARY KEY,
    person_id BIGINT,
    type VARCHAR(50),  -- text, link, image, file
    content TEXT,
    link_url VARCHAR(1000),
    media_keys TEXT[],
    status VARCHAR(50),
    group_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_posts_person ON staging.engagement_posts(person_id);
CREATE INDEX idx_engagement_posts_type ON staging.engagement_posts(type);
CREATE INDEX idx_engagement_posts_created ON staging.engagement_posts(created_at);
CREATE INDEX idx_engagement_posts_deleted ON staging.engagement_posts(deleted_at);

COMMENT ON TABLE staging.engagement_posts IS 'User posts and content';

-- staging.engagement_comments
-- Source: engagement-platform-prd.comments
CREATE TABLE staging.engagement_comments (
    id BIGINT PRIMARY KEY,
    post_id BIGINT,
    person_id BIGINT,
    content TEXT,
    parent_comment_id BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_comments_post ON staging.engagement_comments(post_id);
CREATE INDEX idx_engagement_comments_person ON staging.engagement_comments(person_id);
CREATE INDEX idx_engagement_comments_created ON staging.engagement_comments(created_at);
CREATE INDEX idx_engagement_comments_deleted ON staging.engagement_comments(deleted_at);

COMMENT ON TABLE staging.engagement_comments IS 'Comments on posts';

-- staging.engagement_groups
-- Source: engagement-platform-prd.groups
CREATE TABLE staging.engagement_groups (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_by BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_groups_created_by ON staging.engagement_groups(created_by);
CREATE INDEX idx_engagement_groups_created ON staging.engagement_groups(created_at);
CREATE INDEX idx_engagement_groups_deleted ON staging.engagement_groups(deleted_at);

COMMENT ON TABLE staging.engagement_groups IS 'Community groups';

-- staging.engagement_group_members
-- Source: engagement-platform-prd.group_members
CREATE TABLE staging.engagement_group_members (
    id BIGINT PRIMARY KEY,
    group_id BIGINT,
    person_id BIGINT,
    role VARCHAR(50),
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_members_group ON staging.engagement_group_members(group_id);
CREATE INDEX idx_engagement_members_person ON staging.engagement_group_members(person_id);
CREATE INDEX idx_engagement_members_created ON staging.engagement_group_members(created_at);
CREATE INDEX idx_engagement_members_deleted ON staging.engagement_group_members(deleted_at);

COMMENT ON TABLE staging.engagement_group_members IS 'Group membership records';

-- staging.engagement_mentions
-- Source: engagement-platform-prd.mentions
CREATE TABLE staging.engagement_mentions (
    id BIGINT PRIMARY KEY,
    mentioned_person_id BIGINT,
    post_id BIGINT,
    comment_id BIGINT,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_mentions_person ON staging.engagement_mentions(mentioned_person_id);
CREATE INDEX idx_engagement_mentions_post ON staging.engagement_mentions(post_id);
CREATE INDEX idx_engagement_mentions_created ON staging.engagement_mentions(created_at);
CREATE INDEX idx_engagement_mentions_deleted ON staging.engagement_mentions(deleted_at);

COMMENT ON TABLE staging.engagement_mentions IS 'User mentions in posts/comments';

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'staging'
ORDER BY tablename;

-- Expected: 12 tables (6 chemlink, 6 engagement)

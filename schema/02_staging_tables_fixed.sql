-- ==============================================================================
-- ChemLink Analytics Database - Staging Tables (FIXED - Matches Production)
-- ==============================================================================
-- Purpose: Raw copies from production databases
-- Schema: staging
-- Sync Strategy: Daily ETL
-- NOTE: Schema updated to match actual production column types
-- ==============================================================================

-- Drop existing staging tables
DROP TABLE IF EXISTS staging.chemlink_persons CASCADE;
DROP TABLE IF EXISTS staging.chemlink_experiences CASCADE;
DROP TABLE IF EXISTS staging.chemlink_education CASCADE;
DROP TABLE IF EXISTS staging.chemlink_collections CASCADE;
DROP TABLE IF EXISTS staging.chemlink_query_votes CASCADE;
DROP TABLE IF EXISTS staging.chemlink_view_access CASCADE;
DROP TABLE IF EXISTS staging.engagement_persons CASCADE;
DROP TABLE IF EXISTS staging.engagement_posts CASCADE;
DROP TABLE IF EXISTS staging.engagement_comments CASCADE;
DROP TABLE IF EXISTS staging.engagement_groups CASCADE;
DROP TABLE IF EXISTS staging.engagement_group_members CASCADE;
DROP TABLE IF EXISTS staging.engagement_mentions CASCADE;

-- ==============================================================================
-- CHEMLINK SERVICE STAGING TABLES
-- ==============================================================================

-- staging.chemlink_persons (FIXED to match production)
CREATE TABLE staging.chemlink_persons (
    id BIGINT PRIMARY KEY,
    person_id UUID,
    name VARCHAR(255),
    profile JSON,
    chemlink_id UUID,
    kratos_id UUID,
    hydra_id UUID,
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    secondary_email VARCHAR(255),
    mobile_number VARCHAR(50),
    mobile_number_country_code VARCHAR(10),
    headline_description TEXT,
    linked_in_url VARCHAR(500),
    career_goals TEXT,
    business_experience_summary TEXT,
    profile_picture VARCHAR(500),  -- NOT profile_picture_key
    location_id BIGINT,
    company_id BIGINT,
    role_id BIGINT,
    has_finder BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_persons_email ON staging.chemlink_persons(email);
CREATE INDEX idx_chemlink_persons_created ON staging.chemlink_persons(created_at);
CREATE INDEX idx_chemlink_persons_has_finder ON staging.chemlink_persons(has_finder);
CREATE INDEX idx_chemlink_persons_deleted ON staging.chemlink_persons(deleted_at);

COMMENT ON TABLE staging.chemlink_persons IS 'User profiles from ChemLink Service';

-- Other ChemLink tables remain the same
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

CREATE TABLE staging.chemlink_query_votes (
    id BIGINT PRIMARY KEY,
    voter_id BIGINT,
    query_embedding_id BIGINT,
    vote VARCHAR(50),
    created_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_votes_voter ON staging.chemlink_query_votes(voter_id);

CREATE TABLE staging.chemlink_view_access (
    id BIGINT PRIMARY KEY,
    person_id BIGINT,
    viewed_person_id BIGINT,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chemlink_view_person ON staging.chemlink_view_access(person_id);

-- ==============================================================================
-- ENGAGEMENT PLATFORM STAGING TABLES (FIXED to use UUID)
-- ==============================================================================

-- staging.engagement_persons (FIXED: id and external_id are now correct types)
CREATE TABLE staging.engagement_persons (
    id UUID PRIMARY KEY,  -- UUID not BIGINT!
    external_id VARCHAR(255),  -- VARCHAR not BIGINT!
    iam_id VARCHAR(255),
    email VARCHAR(255),
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
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

COMMENT ON TABLE staging.engagement_persons IS 'Social platform profiles (external_id links to ChemLink)';

-- staging.engagement_posts (id is UUID)
CREATE TABLE staging.engagement_posts (
    id UUID PRIMARY KEY,  -- UUID not BIGINT!
    person_id UUID,  -- UUID not BIGINT!
    type VARCHAR(50),
    content TEXT,
    link_url VARCHAR(1000),
    media_keys TEXT[],
    status VARCHAR(50),
    group_id UUID,  -- UUID not BIGINT!
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_posts_person ON staging.engagement_posts(person_id);

-- staging.engagement_comments (UUIDs)
CREATE TABLE staging.engagement_comments (
    id UUID PRIMARY KEY,
    post_id UUID,
    person_id UUID,
    content TEXT,
    parent_comment_id UUID,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_engagement_comments_person ON staging.engagement_comments(person_id);

-- staging.engagement_groups (UUIDs)
CREATE TABLE staging.engagement_groups (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_by UUID,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- staging.engagement_group_members (UUIDs)
CREATE TABLE staging.engagement_group_members (
    id UUID PRIMARY KEY,
    group_id UUID,
    person_id UUID,
    role VARCHAR(50),
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- staging.engagement_mentions (UUIDs)
CREATE TABLE staging.engagement_mentions (
    id UUID PRIMARY KEY,
    mentioned_person_id UUID,
    post_id UUID,
    comment_id UUID,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE staging.engagement_mentions IS 'User mentions in posts/comments';

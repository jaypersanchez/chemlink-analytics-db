-- ==============================================================================
-- Neo4j Graph Data Integration Schema
-- ==============================================================================
-- Creates staging, core, and aggregates tables for Neo4j graph data
-- Run against: chemlink_analytics database
-- Date: 2025-11-10
-- ==============================================================================

-- ==============================================================================
-- STAGING SCHEMA - Raw Neo4j Data Copy
-- ==============================================================================

-- Staging: Person nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_persons (
    person_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255),
    secondary_email VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    mobile_number VARCHAR(50),
    mobile_number_country_code VARCHAR(10),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_neo4j_persons_email ON staging.neo4j_persons(email);

-- Staging: Company nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_companies (
    company_id VARCHAR(255) PRIMARY KEY,
    company_name VARCHAR(500),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_neo4j_companies_name ON staging.neo4j_companies(company_name);

-- Staging: Role nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_roles (
    role_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_neo4j_roles_title ON staging.neo4j_roles(title);

-- Staging: School nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_schools (
    school_id VARCHAR(255) PRIMARY KEY,
    school_name VARCHAR(500),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_neo4j_schools_name ON staging.neo4j_schools(school_name);

-- Staging: Degree nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_degrees (
    degree_id VARCHAR(255) PRIMARY KEY,
    degree_name VARCHAR(255),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Location nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_locations (
    location_id VARCHAR(255) PRIMARY KEY,
    country VARCHAR(255),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Project nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_projects (
    project_id VARCHAR(255) PRIMARY KEY,
    project_name VARCHAR(500),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Language nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_languages (
    language_id VARCHAR(255) PRIMARY KEY,
    language_name VARCHAR(255),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Experience nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_experiences (
    experience_id VARCHAR(255) PRIMARY KEY,
    start_date DATE,
    end_date DATE,
    type VARCHAR(100),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Education nodes
CREATE TABLE IF NOT EXISTS staging.neo4j_educations (
    education_id VARCHAR(255) PRIMARY KEY,
    start_date DATE,
    end_date DATE,
    field_of_study VARCHAR(500),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging: Relationships (edge list)
CREATE TABLE IF NOT EXISTS staging.neo4j_relationships (
    id SERIAL PRIMARY KEY,
    source_node_id VARCHAR(255),
    source_node_type VARCHAR(50),
    relationship_type VARCHAR(100),
    target_node_id VARCHAR(255),
    target_node_type VARCHAR(50),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_neo4j_rels_source ON staging.neo4j_relationships(source_node_id, source_node_type);
CREATE INDEX IF NOT EXISTS idx_neo4j_rels_target ON staging.neo4j_relationships(target_node_id, target_node_type);
CREATE INDEX IF NOT EXISTS idx_neo4j_rels_type ON staging.neo4j_relationships(relationship_type);

-- ==============================================================================
-- CORE SCHEMA - Unified, Cleaned Graph Data
-- ==============================================================================

-- Core: User-to-User Relationships (normalized graph edges)
CREATE TABLE IF NOT EXISTS core.user_relationships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    related_user_id INTEGER NOT NULL,
    relationship_type VARCHAR(100) NOT NULL, -- WORKED_TOGETHER, STUDIED_TOGETHER, SAME_LOCATION, SAME_COMPANY
    relationship_strength INTEGER DEFAULT 1,
    connection_context JSONB, -- {"companies": ["Acme Inc"], "schools": ["MIT"], "roles": ["Engineer"]}
    first_connected_at TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, related_user_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_user_rels_user ON core.user_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_user_rels_related ON core.user_relationships(related_user_id);
CREATE INDEX IF NOT EXISTS idx_user_rels_type ON core.user_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_user_rels_strength ON core.user_relationships(relationship_strength DESC);

-- Core: Career Paths (experience progression)
CREATE TABLE IF NOT EXISTS core.career_paths (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    experience_sequence JSONB NOT NULL, -- [{"role": "Engineer", "company": "Acme", "years": 2, "start": "2020-01", "end": "2022-01"}]
    path_vector TEXT, -- "Engineer->Senior Engineer->Lead Engineer" for pattern matching
    total_years_experience INTEGER,
    number_of_roles INTEGER,
    number_of_companies INTEGER,
    path_hash VARCHAR(64), -- MD5 hash of path_vector for grouping similar paths
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_career_paths_user ON core.career_paths(user_id);
CREATE INDEX IF NOT EXISTS idx_career_paths_vector ON core.career_paths(path_vector);
CREATE INDEX IF NOT EXISTS idx_career_paths_hash ON core.career_paths(path_hash);

-- Core: Education Networks (school-based connections)
CREATE TABLE IF NOT EXISTS core.education_networks (
    id SERIAL PRIMARY KEY,
    school_id VARCHAR(255) NOT NULL,
    school_name VARCHAR(500),
    degree_id VARCHAR(255),
    degree_name VARCHAR(255),
    user_ids INTEGER[] NOT NULL,
    user_count INTEGER NOT NULL,
    graduation_year_min INTEGER,
    graduation_year_max INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_education_networks_school ON core.education_networks(school_id);
CREATE INDEX IF NOT EXISTS idx_education_networks_degree ON core.education_networks(degree_id);
CREATE INDEX IF NOT EXISTS idx_education_networks_user_count ON core.education_networks(user_count DESC);

-- Core: Company Networks (company-based connections)
CREATE TABLE IF NOT EXISTS core.company_networks (
    id SERIAL PRIMARY KEY,
    company_id VARCHAR(255) NOT NULL,
    company_name VARCHAR(500),
    role_id VARCHAR(255),
    role_title VARCHAR(500),
    user_ids INTEGER[] NOT NULL,
    user_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_company_networks_company ON core.company_networks(company_id);
CREATE INDEX IF NOT EXISTS idx_company_networks_role ON core.company_networks(role_id);
CREATE INDEX IF NOT EXISTS idx_company_networks_user_count ON core.company_networks(user_count DESC);

-- Core: Location Networks
CREATE TABLE IF NOT EXISTS core.location_networks (
    id SERIAL PRIMARY KEY,
    location_id VARCHAR(255) NOT NULL,
    country VARCHAR(255),
    user_ids INTEGER[] NOT NULL,
    user_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_location_networks_location ON core.location_networks(location_id);
CREATE INDEX IF NOT EXISTS idx_location_networks_user_count ON core.location_networks(user_count DESC);

-- Core: Project Collaborations
CREATE TABLE IF NOT EXISTS core.project_collaborations (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    project_name VARCHAR(500),
    company_id VARCHAR(255),
    user_ids INTEGER[] NOT NULL,
    user_count INTEGER NOT NULL,
    role_ids TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_project_collab_project ON core.project_collaborations(project_id);
CREATE INDEX IF NOT EXISTS idx_project_collab_company ON core.project_collaborations(company_id);

-- ==============================================================================
-- AGGREGATES SCHEMA - Pre-Calculated Dashboard Metrics
-- ==============================================================================

-- Aggregate 1: Connection Recommendations ("People You Should Know")
CREATE TABLE IF NOT EXISTS aggregates.connection_recommendations (
    user_id INTEGER NOT NULL,
    recommended_user_id INTEGER NOT NULL,
    recommendation_score DECIMAL(5,2) NOT NULL,
    common_companies TEXT[],
    common_roles TEXT[],
    common_schools TEXT[],
    common_locations TEXT[],
    common_projects TEXT[],
    recommendation_reason VARCHAR(500),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, recommended_user_id)
);

CREATE INDEX IF NOT EXISTS idx_conn_recs_user ON aggregates.connection_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_conn_recs_score ON aggregates.connection_recommendations(recommendation_score DESC);

-- Aggregate 2: Company Network Map
CREATE TABLE IF NOT EXISTS aggregates.company_network_map (
    company_id_1 VARCHAR(255) NOT NULL,
    company_id_2 VARCHAR(255) NOT NULL,
    company_name_1 VARCHAR(500),
    company_name_2 VARCHAR(500),
    shared_employee_count INTEGER NOT NULL,
    employee_ids INTEGER[],
    network_strength_score DECIMAL(5,2),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id_1, company_id_2)
);

CREATE INDEX IF NOT EXISTS idx_company_net_company1 ON aggregates.company_network_map(company_id_1);
CREATE INDEX IF NOT EXISTS idx_company_net_company2 ON aggregates.company_network_map(company_id_2);
CREATE INDEX IF NOT EXISTS idx_company_net_strength ON aggregates.company_network_map(network_strength_score DESC);

-- Aggregate 3: Skills & Role Matching
CREATE TABLE IF NOT EXISTS aggregates.skills_matching_scores (
    user_id INTEGER NOT NULL,
    role_id VARCHAR(255) NOT NULL,
    role_title VARCHAR(500),
    experience_years DECIMAL(4,1),
    proficiency_score DECIMAL(5,2),
    similar_user_ids INTEGER[],
    similar_user_count INTEGER,
    role_transition_paths TEXT[], -- ["Engineer->Senior Engineer", "Engineer->Lead"]
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_skills_match_user ON aggregates.skills_matching_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_skills_match_role ON aggregates.skills_matching_scores(role_id);
CREATE INDEX IF NOT EXISTS idx_skills_match_score ON aggregates.skills_matching_scores(proficiency_score DESC);

-- Aggregate 4: Career Path Patterns
CREATE TABLE IF NOT EXISTS aggregates.career_path_patterns (
    path_id SERIAL PRIMARY KEY,
    path_vector TEXT NOT NULL,
    path_hash VARCHAR(64) NOT NULL,
    role_sequence TEXT[] NOT NULL,
    company_sequence TEXT[],
    avg_years_per_role DECIMAL(4,1),
    user_count INTEGER NOT NULL,
    user_ids INTEGER[],
    success_rate DECIMAL(5,2), -- % who progressed to next level
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(path_hash)
);

CREATE INDEX IF NOT EXISTS idx_career_patterns_hash ON aggregates.career_path_patterns(path_hash);
CREATE INDEX IF NOT EXISTS idx_career_patterns_user_count ON aggregates.career_path_patterns(user_count DESC);

-- Aggregate 5: Location-Based Networks
CREATE TABLE IF NOT EXISTS aggregates.location_based_networks (
    location_id VARCHAR(255) PRIMARY KEY,
    country VARCHAR(255),
    user_ids INTEGER[] NOT NULL,
    user_count INTEGER NOT NULL,
    company_diversity_score DECIMAL(5,2), -- How many different companies represented
    role_diversity_score DECIMAL(5,2), -- How many different roles represented
    top_companies TEXT[],
    top_roles TEXT[],
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_location_net_user_count ON aggregates.location_based_networks(user_count DESC);
CREATE INDEX IF NOT EXISTS idx_location_net_diversity ON aggregates.location_based_networks(company_diversity_score DESC);

-- Aggregate 6: Alumni Networks
CREATE TABLE IF NOT EXISTS aggregates.alumni_networks (
    school_id VARCHAR(255) NOT NULL,
    school_name VARCHAR(500),
    degree_id VARCHAR(255) NOT NULL DEFAULT 'ALL',
    degree_name VARCHAR(255),
    user_ids INTEGER[] NOT NULL,
    alumni_count INTEGER NOT NULL,
    graduation_year_min INTEGER,
    graduation_year_max INTEGER,
    current_companies TEXT[], -- Top companies alumni work at
    current_roles TEXT[], -- Top roles alumni hold
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (school_id, degree_id)
);

CREATE INDEX IF NOT EXISTS idx_alumni_net_school ON aggregates.alumni_networks(school_id);
CREATE INDEX IF NOT EXISTS idx_alumni_net_degree ON aggregates.alumni_networks(degree_id);
CREATE INDEX IF NOT EXISTS idx_alumni_net_count ON aggregates.alumni_networks(alumni_count DESC);

-- Aggregate 7: Project Collaboration Graph
CREATE TABLE IF NOT EXISTS aggregates.project_collaboration_graph (
    project_id VARCHAR(255) NOT NULL,
    project_name VARCHAR(500),
    company_id VARCHAR(255),
    company_name VARCHAR(500),
    user_ids INTEGER[] NOT NULL,
    user_count INTEGER NOT NULL,
    role_ids TEXT[],
    collaboration_strength DECIMAL(5,2), -- Based on # of shared projects, roles, etc.
    project_start_date DATE,
    project_end_date DATE,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE aggregates.project_collaboration_graph
    DROP CONSTRAINT IF EXISTS project_collaboration_graph_pkey;
ALTER TABLE aggregates.project_collaboration_graph
    ADD CONSTRAINT project_collaboration_graph_pkey PRIMARY KEY (project_id, company_id);

CREATE INDEX IF NOT EXISTS idx_project_collab_graph_company ON aggregates.project_collaboration_graph(company_id);
CREATE INDEX IF NOT EXISTS idx_project_collab_graph_user_count ON aggregates.project_collaboration_graph(user_count DESC);
CREATE INDEX IF NOT EXISTS idx_project_collab_graph_strength ON aggregates.project_collaboration_graph(collaboration_strength DESC);

-- ==============================================================================
-- HELPER VIEWS
-- ==============================================================================

-- View: User connection summary
CREATE OR REPLACE VIEW aggregates.user_connection_summary AS
SELECT 
    user_id,
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE relationship_type = 'WORKED_TOGETHER') as work_connections,
    COUNT(*) FILTER (WHERE relationship_type = 'STUDIED_TOGETHER') as school_connections,
    COUNT(*) FILTER (WHERE relationship_type = 'SAME_LOCATION') as location_connections,
    AVG(relationship_strength) as avg_connection_strength
FROM core.user_relationships
GROUP BY user_id;

-- View: Top connected users (influencers)
CREATE OR REPLACE VIEW aggregates.top_connected_users AS
SELECT 
    u.chemlink_id,
    u.email,
    u.first_name,
    u.last_name,
    COUNT(DISTINCT r.related_user_id) as connection_count,
    AVG(r.relationship_strength) as avg_connection_strength
FROM core.unified_users u
LEFT JOIN core.user_relationships r ON u.chemlink_id = r.user_id
WHERE u.deleted_at IS NULL
GROUP BY u.chemlink_id, u.email, u.first_name, u.last_name
ORDER BY connection_count DESC
LIMIT 100;

-- View: Company talent pools
CREATE OR REPLACE VIEW aggregates.company_talent_pools AS
SELECT 
    cn.company_id,
    cn.company_name,
    COUNT(DISTINCT unnest(cn.user_ids)) as total_employees,
    array_agg(DISTINCT cn.role_title) as roles_available,
    COUNT(DISTINCT cn.role_id) as role_diversity
FROM core.company_networks cn
GROUP BY cn.company_id, cn.company_name
ORDER BY total_employees DESC;

-- ==============================================================================
-- METADATA TABLE
-- ==============================================================================

CREATE TABLE IF NOT EXISTS meta.neo4j_extraction_log (
    id SERIAL PRIMARY KEY,
    extraction_type VARCHAR(50), -- 'full' or 'incremental'
    nodes_extracted INTEGER,
    relationships_extracted INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20), -- 'success', 'failed', 'in_progress'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- COMMENTS
-- ==============================================================================

COMMENT ON TABLE staging.neo4j_relationships IS 'Edge list from Neo4j - all relationships between nodes';
COMMENT ON TABLE core.user_relationships IS 'Normalized user-to-user connections derived from Neo4j graph';
COMMENT ON TABLE aggregates.connection_recommendations IS 'Pre-calculated connection suggestions for dashboard';
COMMENT ON TABLE aggregates.company_network_map IS 'Company-to-company network graph based on employee overlap';
COMMENT ON TABLE aggregates.skills_matching_scores IS 'User skill/role similarity scores for matching';
COMMENT ON TABLE aggregates.career_path_patterns IS 'Common career progression patterns identified from user experiences';
COMMENT ON TABLE aggregates.location_based_networks IS 'User networks grouped by geographic location';
COMMENT ON TABLE aggregates.alumni_networks IS 'School-based networks showing alumni connections';
COMMENT ON TABLE aggregates.project_collaboration_graph IS 'Project-based collaboration networks';

-- ==============================================================================
-- GRANTS (if needed)
-- ==============================================================================

-- Grant read access to dashboard user (adjust as needed)
-- GRANT SELECT ON ALL TABLES IN SCHEMA aggregates TO dashboard_user;

-- ==============================================================================
-- SCHEMA CREATION COMPLETE
-- ==============================================================================

-- Verify table creation
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname IN ('staging', 'core', 'aggregates')
    AND tablename LIKE '%neo4j%' 
    OR tablename IN (
        'connection_recommendations',
        'company_network_map',
        'skills_matching_scores',
        'career_path_patterns',
        'location_based_networks',
        'alumni_networks',
        'project_collaboration_graph',
        'user_relationships',
        'career_paths',
        'education_networks',
        'company_networks',
        'location_networks',
        'project_collaborations'
    )
ORDER BY schemaname, tablename;

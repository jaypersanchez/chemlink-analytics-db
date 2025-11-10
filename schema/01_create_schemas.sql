-- ==============================================================================
-- ChemLink Analytics Database - Schema Creation
-- ==============================================================================
-- Purpose: Create the four main schemas for organizing analytics data
-- Author: Analytics DB Project
-- Created: 2025-11-04
-- ==============================================================================

-- Drop schemas if they exist (for clean reinstall)
DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS core CASCADE;
DROP SCHEMA IF EXISTS aggregates CASCADE;
DROP SCHEMA IF EXISTS ai CASCADE;

-- ==============================================================================
-- STAGING SCHEMA
-- ==============================================================================
-- Purpose: Raw copies of data from production databases
-- Data Flow: Production DBs → staging (via ETL)
-- Refresh: Daily full/incremental
-- ==============================================================================

CREATE SCHEMA staging;
COMMENT ON SCHEMA staging IS 'Raw data copied from production databases (ChemLink Service + Engagement Platform)';

-- ==============================================================================
-- CORE SCHEMA
-- ==============================================================================
-- Purpose: Cleaned, unified, and transformed data
-- Data Flow: staging → core (via ETL transformation)
-- Refresh: Daily
-- ==============================================================================

CREATE SCHEMA core;
COMMENT ON SCHEMA core IS 'Cleaned and unified data combining both source databases';

-- ==============================================================================
-- AGGREGATES SCHEMA
-- ==============================================================================
-- Purpose: Pre-calculated metrics and materialized views for dashboards
-- Data Flow: core → aggregates (via scheduled jobs)
-- Refresh: Daily/Weekly/Monthly depending on table
-- ==============================================================================

CREATE SCHEMA aggregates;
COMMENT ON SCHEMA aggregates IS 'Pre-calculated metrics and aggregations for fast dashboard queries';

-- ==============================================================================
-- AI SCHEMA
-- ==============================================================================
-- Purpose: Training datasets for machine learning models
-- Data Flow: core + aggregates → ai (via feature engineering)
-- Refresh: Monthly (for training runs)
-- ==============================================================================

CREATE SCHEMA ai;
COMMENT ON SCHEMA ai IS 'Feature-engineered datasets for Alchemi AI training';

-- ==============================================================================
-- VERIFICATION
-- ==============================================================================

SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name IN ('staging', 'core', 'aggregates', 'ai')
ORDER BY schema_name;

-- Expected output: 4 rows (ai, aggregates, core, staging)

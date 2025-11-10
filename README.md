# ChemLink Analytics Database

**Unified analytics database combining data from ChemLink Service and Engagement Platform for cross-database analytics and AI training data.**

---

## 🎯 Purpose

This project creates a **local analytics database** that:
- Combines data from two production databases (read-only access)
- Provides unified views for cross-database analytics
- Pre-calculates aggregated metrics for performance
- Exports clean datasets for Alchemi AI training
- Enables cohort analysis and user journey tracking

---

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐
│ engagement-platform │    │ chemlink-service    │
│ (Social Features)   │    │ (Profile/Finder)    │
│    PRODUCTION       │    │    PRODUCTION       │
│    READ-ONLY        │    │    READ-ONLY        │
└──────────┬──────────┘    └──────────┬──────────┘
           │                          │
           │  ETL Pipeline (Python)   │
           └────────┬─────────────────┘
                    ↓
         ┌──────────────────────┐
         │  Analytics Database  │
         │     LOCALHOST        │
         │    PostgreSQL        │
         │                      │
         │  • staging/          │
         │  • core/             │
         │  • aggregates/       │
         │  • ai/               │
         └──────────────────────┘
```

---

## 📊 Database Schema

### Schema Organization

**`staging`** - Raw data copied from source databases  
**`core`** - Cleaned, transformed, and unified data  
**`aggregates`** - Materialized views for dashboards  
**`ai`** - Training datasets for machine learning

### Key Tables/Views

- `core.unified_users` - Master user table combining both DBs
- `aggregates.daily_metrics` - Pre-calculated daily KPIs
- `aggregates.cohort_retention` - Retention analysis
- `core.user_journey_events` - Lifecycle event tracking
- `ai.training_data_activation` - ML features for activation prediction
- `ai.training_data_engagement` - ML features for engagement prediction

---

## 🚀 Setup

### Prerequisites

- Python 3.8+
- PostgreSQL 14+ (installed locally)
- Access to ChemLink production databases (read-only credentials)

### Installation

1. **Create local analytics database**
   ```bash
   psql -U postgres
   CREATE DATABASE chemlink_analytics;
   \q
   ```

2. **Clone/navigate to project**
   ```bash
   cd ~/projects/chemlink-analytics-db
   ```

3. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your local postgres credentials
   ```

6. **Initialize schema**
   ```bash
   python scripts/init_schema.py
   ```

7. **Run ETL pipeline**
   ```bash
   python scripts/etl_pipeline.py
   ```

---

## 📁 Project Structure

```
chemlink-analytics-db/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env                        # Configuration (not in git)
├── .env.example                # Template for credentials
├── db_config.py                # Database connection helpers
├── schema/
│   ├── 01_create_schemas.sql   # Schema definitions
│   ├── 02_staging_tables.sql   # Staging layer tables
│   ├── 03_core_tables.sql      # Core layer tables
│   ├── 04_aggregate_views.sql  # Materialized views
│   └── 05_ai_views.sql         # AI training data views
├── scripts/
│   ├── init_schema.py          # Initialize database schema
│   ├── etl_pipeline.py         # Main ETL orchestrator
│   ├── extract.py              # Extract from source DBs
│   ├── transform.py            # Transform and clean data
│   └── load.py                 # Load into analytics DB
├── tests/
│   ├── test_connections.py     # Test DB connections
│   ├── test_etl.py             # Test ETL pipeline
│   └── test_data_quality.py    # Validate data integrity
└── docs/
    ├── ARCHITECTURE.md          # Technical design details
    ├── ETL_DESIGN.md           # ETL pipeline documentation
    └── SCHEMA_DESIGN.md        # Database schema details
```

---

## 🔄 ETL Pipeline

### Extract
Pulls data from production databases (read-only):
- `chemlink-service-prd`
- `engagement-platform-prd`

### Transform
- Joins data using `external_id` relationship
- Calculates derived metrics (profile_completion_score, engagement_score)
- Cleans data (removes test accounts, validates consistency)
- Handles soft deletes properly

### Load
- Inserts into staging schema
- Transforms into core schema
- Refreshes materialized views
- Exports AI training datasets

### Running the Pipeline

**Full refresh:**
```bash
python scripts/etl_pipeline.py --full
```

**Incremental update:**
```bash
python scripts/etl_pipeline.py --incremental
```

**Specific date range:**
```bash
python scripts/etl_pipeline.py --start-date 2025-10-01 --end-date 2025-10-31
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

```bash
# Source Database - ChemLink Service (Production, Read-Only)
CHEMLINK_PRD_DB_HOST=...
CHEMLINK_PRD_DB_PORT=5432
CHEMLINK_PRD_DB_NAME=chemlink-service-prd
CHEMLINK_PRD_DB_USER=chemlink-readonly
CHEMLINK_PRD_DB_PASSWORD=...

# Source Database - Engagement Platform (Production, Read-Only)
ENGAGEMENT_PRD_DB_HOST=...
ENGAGEMENT_PRD_DB_PORT=5432
ENGAGEMENT_PRD_DB_NAME=engagement-platform-prd
ENGAGEMENT_PRD_DB_USER=chemlink-readonly
ENGAGEMENT_PRD_DB_PASSWORD=...

# Analytics Database (Local)
ANALYTICS_DB_HOST=localhost
ANALYTICS_DB_PORT=5432
ANALYTICS_DB_NAME=chemlink_analytics
ANALYTICS_DB_USER=postgres
ANALYTICS_DB_PASSWORD=your_local_password

# ETL Configuration
ETL_BATCH_SIZE=1000
ETL_LOG_LEVEL=INFO
```

---

## 📊 Key Metrics Provided

### User Analytics
- New signups (daily/weekly/monthly)
- Growth rates
- User segmentation (Finder vs Standard)
- Profile completion rates

### Activity Analytics
- DAU/WAU/MAU (comprehensive, not just social)
- Activity by type (posts, comments, votes, collections, etc.)
- Engagement intensity levels
- Content type distribution

### Cohort Analytics
- Retention by signup cohort
- Activation rates
- Time-to-activation
- Churn analysis

### AI Training Data
- User activation prediction features
- Engagement level prediction features
- Behavioral pattern datasets
- Clean labeled data for ML models

---

## 🎯 Success Criteria

### Phase 1: Foundation ✅
- [x] Analytics DB created locally
- [ ] Schema designed and implemented
- [ ] ETL pipeline extracts from both source DBs
- [ ] Unified user view working

### Phase 2: Analytics
- [ ] Daily metrics aggregation running
- [ ] Cohort analysis tables populated
- [ ] User journey tracking implemented
- [ ] Dashboard queries 10x faster

### Phase 3: AI Readiness
- [ ] Clean training datasets exported
- [ ] Features engineered for ML models
- [ ] Historical data preserved properly
- [ ] Alchemi AI can consume data easily

---

## 🔗 Related Projects

**Source Project:** `chemlink-analytics-dashboard`
- Current Flask dashboard (direct DB queries)
- Reference for required metrics
- Context document: `ANALYTICS_DB_CONTEXT.md`

**Future Integration:**
Dashboard will eventually query this analytics DB instead of production databases directly.

---

## 📚 Documentation

- `/docs/ARCHITECTURE.md` - Technical design and decisions
- `/docs/ETL_DESIGN.md` - ETL pipeline details
- `/docs/SCHEMA_DESIGN.md` - Database schema documentation
- `../chemlink-analytics-dashboard/ANALYTICS_DB_CONTEXT.md` - Full context handoff

---

## 🚨 Important Notes

- **Production databases are READ-ONLY** - We never write to them
- **Local database only** - All transformations happen locally
- **No PII exposed** - Analytics data is aggregated and anonymized where needed
- **Incremental updates** - Pipeline supports both full and incremental refreshes

---

## 🤝 Contributing

1. Always test ETL scripts on small datasets first
2. Document any new metrics or transformations
3. Keep schema migrations in separate SQL files
4. Update README when adding new features

---

## 📧 Support

Questions? Reference the context document:
`../chemlink-analytics-dashboard/ANALYTICS_DB_CONTEXT.md`

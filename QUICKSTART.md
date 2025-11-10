# Quick Start Guide

**Get the analytics database up and running in 5 minutes**

---

## Step 1: Setup Local Database

```bash
# Create the analytics database
psql -U postgres
CREATE DATABASE chemlink_analytics;
\q
```

---

## Step 2: Configure Environment

Edit `.env` file and set your local postgres password:

```bash
# Find this line:
ANALYTICS_DB_PASSWORD=

# Set it to your local postgres password:
ANALYTICS_DB_PASSWORD=your_actual_password
```

**Note:** Production read-only credentials are already configured in `.env`

---

## Step 3: Install Dependencies

```bash
cd ~/projects/chemlink-analytics-db

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

---

## Step 4: Test Connections

```bash
python test_setup.py
```

**Expected output:**
```
======================================================================
ChemLink Analytics Database - Setup Test
======================================================================

✅ .env file found

======================================================================
Testing Database Connections...
======================================================================

chemlink_source:
  ✅ Connected successfully
  └─ Active users: 2,094

engagement_source:
  ✅ Connected successfully
  └─ Active users: 2

analytics_db:
  ✅ Connected successfully
  └─ PostgreSQL 14.x ...

======================================================================
✅ All connections successful! Ready to proceed.
======================================================================
```

---

## Step 5: What's Next?

Now you're ready to:

1. **Design the schema** (`schema/` directory)
2. **Build ETL pipeline** (`scripts/` directory)
3. **Create materialized views** for analytics
4. **Export AI training data**

---

## 📚 Reference Documents

- `README.md` - Full project documentation
- `CONTEXT.md` → Links to `../chemlink-analytics-dashboard/ANALYTICS_DB_CONTEXT.md`
  - Complete requirements and context from dashboard project
  - All findings from analytics deep dive
  - Schema design proposals

---

## 🎯 Project Goal

Build a local analytics database that:
- ✅ Pulls data from production (read-only)
- ✅ Combines ChemLink + Engagement databases
- ✅ Pre-calculates metrics for dashboards
- ✅ Exports clean data for AI training

---

## 🚨 Important Reminders

- **Production DBs are READ-ONLY** - We never write to them
- **Local database only** - All transformations happen here
- **Use prod data** - Most complete and accurate dataset
- **Clean test data** - Remove ghost accounts during ETL

---

## 💡 Tips

**Test connections first:**
```bash
python test_setup.py
```

**Check context document:**
```bash
cat CONTEXT.md  # or open in editor
```

**Read full documentation:**
```bash
cat README.md
```

---

**Questions? Check CONTEXT.md for complete requirements and architecture details.**

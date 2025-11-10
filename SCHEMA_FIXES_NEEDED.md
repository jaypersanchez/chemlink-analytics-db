# Schema Fixes Needed for ETL Extraction

## ✅ Progress So Far

- Schemas created: staging, core, aggregates, ai
- Staging tables: Partially fixed
- First successful table: **staging.chemlink_collections** (7 rows loaded!)
- Extraction script: Working with verbose logging and timing

---

## ❌ Remaining Issues

### 1. **JSON Column Handling** - chemlink_persons.profile
**Error:** `can't adapt type 'dict'`

**Solution:** Convert JSON column to string before insert:
```python
# In extract script, convert profile dict to JSON string
import json
if row_has_profile:
    row['profile'] = json.dumps(row['profile'])
```

### 2. **Invalid Date Format** - experiences/education dates
**Error:** `invalid input syntax for type date: "4-2011"` and `"1-2019"`

**Problem:** Production stores dates as "MM-YYYY" strings, not proper dates

**Solutions:**
- Option A: Change staging table columns to VARCHAR
- Option B: Parse and convert dates in extract script
- **Recommended:** Use VARCHAR in staging (keep raw data), parse in transform step

### 3. **Missing Column** - query_votes.query_embedding_id
**Error:** `column "query_embedding_id" does not exist`

**Solution:** Check actual production schema:
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_name='query_votes' ORDER BY ordinal_position;
```

Then update staging table definition.

### 4. **Engagement Platform UUIDs** - Not yet tested
Staging tables fixed but extract script not yet run on engagement data.

---

## 🔧 Quick Fixes Required

### File: `/schema/02_staging_tables_fixed.sql`

**Change date columns to VARCHAR:**
```sql
-- experiences
start_date VARCHAR(50),  -- was DATE
end_date VARCHAR(50),    -- was DATE

-- education  
start_date VARCHAR(50),  -- was DATE
end_date VARCHAR(50),    -- was DATE
```

### File: `/scripts/extract.py`

**Add JSON serialization:**
```python
# After fetching rows from ChemLink persons
for i, row in enumerate(rows):
    row_list = list(row)
    # Profile is column 3 (0-indexed)
    if row_list[3] is not None:  # profile column
        row_list[3] = json.dumps(row_list[3])
    rows[i] = tuple(row_list)
```

**Remove query_embedding_id column** until we verify it exists.

---

## 📊 What's Working

✅ Database connections  
✅ Verbose logging with timing  
✅ Error handling and graceful failures  
✅ Progress tracking  
✅ Summary statistics  
✅ Orphan filtering logic  
✅ First successful table load (collections)!

---

## 🎯 Next Steps

1. Check actual `query_votes` schema in production
2. Apply date column fixes (VARCHAR instead of DATE)
3. Add JSON serialization for `profile` column
4. Re-run extraction
5. Complete transform script (staging → core)

---

**Session ended at token limit. Continue in new session with this context.**

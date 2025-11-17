# Kratos Identity Integration – Progress & Next Steps

Operational checklist for bringing Kratos identity/authentication data into the ChemLink analytics pipeline (kube-focused).

---

## 1. Environment Alignment (✅)
- `.env` / `.env.example` now include `DATA_ENV` plus `KRATOS_PRD_DB_*` and `KRATOS_DEV_DB_*` values.
- When `DATA_ENV=kube`, all ETL helpers target the Kubernetes port-forward (`localhost:5433`) for ChemLink, Engagement, Analytics, and Kratos databases.
- Kubectl command we rely on:
  ```bash
  kubectl port-forward svc/psql-postgresql 5433:5432 -n utils --kubeconfig global-develop-kubeconfig
  ```
- Verifications (run locally, outside the sandbox):
  ```bash
  nc -vz localhost 5433
  PGPASSWORD=dev psql -h localhost -p 5433 -U dev -d kratos-chemlink-dev -c 'select 1'
  ```

## 2. Staging Schema (✅)
- Added four landing tables in `schema/02_staging_tables.sql` (and the `_fixed` variant):
  - `staging.kratos_identities`
  - `staging.kratos_identity_credentials`
  - `staging.kratos_sessions`
  - `staging.kratos_session_devices`
- Each table captures raw JSON/metadata plus sync timestamps and indexes so downstream transforms can join quickly.

## 3. Extract Scripts (✅)
- `scripts/extract.py` (full refresh) and `scripts/extract_incremental.py` (upsert mode) now:
  - Open a Kratos source connection via `get_kratos_source_connection()`.
  - Use adaptive column discovery so Dev/Prod schema drift doesn't break the run.
  - Load the four staging tables after the ChemLink + Engagement sections.
  - **Fixed**: JSON/JSONB columns (dicts/lists) are now properly serialized to JSON strings
  - **Fixed**: `identity_credentials` now properly JOINs with `identity_credential_types`
- Run sequence (once port-forward is live):
  ```bash
  DATA_ENV=kube python scripts/extract.py         # full refresh
  DATA_ENV=kube python scripts/extract_incremental.py  # future nightly top-offs
  ```
- **Status**: ✅ Working! Successfully extracted:
  - `kratos_identities`: 177 rows
  - `kratos_identity_credentials`: 177 rows  
  - `kratos_sessions`: 1,814 rows
  - `kratos_session_devices`: 0 rows (table doesn't exist in Kratos schema)

---

## 4. Transform Kratos → Core (✅)
- **Integrated Kratos data into `core.unified_users`** table with new columns:
  - `kratos_identity_id` (UUID) - Link to Kratos identity
  - `kratos_identity_state` (VARCHAR) - Account state (active/inactive)
  - `last_login_at` (TIMESTAMP) - Most recent authentication
  - `total_sessions` (INTEGER) - Lifetime session count
  - `active_sessions` (INTEGER) - Currently active sessions
  - `mfa_enabled` (BOOLEAN) - Has TOTP/WebAuthn configured
  - `highest_aal` (VARCHAR) - Highest authentication assurance level achieved
  - `account_locked` (BOOLEAN) - Account lock status
  - `credential_type` (VARCHAR) - Primary credential type (password/totp/webauthn)
- **Updated `scripts/transform.py`**:
  - Added LEFT JOINs to `staging.kratos_identities` and `staging.kratos_identity_credentials`
  - Subqueries calculate session metrics from `staging.kratos_sessions`
  - Type casting for `kratos_id` VARCHAR → UUID
  - DISTINCT ON to handle multiple credentials per user
- **Status**: ✅ Working! Transformed 2,146 users:
  - 61 users matched with Kratos identities
  - 38 users have login history
  - 0 users with MFA enabled
  - Max sessions per user: 367

## 5. Next Steps (🚧)
1. **Enhance Aggregates / AI Views**

1. **Enhance Aggregates / AI Views**
   - Add materialized views for `aggregates.auth_health_daily`, `aggregates.login_velocity`, etc.
   - Extend `ai.activation_training_data` / `ai.engagement_training_data` with auth-based features (MFA flag, login streak, failed logins).

2. **Quality Gates & Monitoring**
   - Add tests under `tests/` to ensure Kratos tables populate (row counts > 0, identity/session counts match source).
   - Incorporate auth metrics into existing dashboards or create `/api/auth/*` routes in V2.

3. **Operational Runbook**
   - Document port-forward + ETL steps in `docs/` (this file is the starting point).
   - Add alerts/observability once auth data drives production decisions.

---

## Quick Verification (once transforms land)
```bash
# Check staging counts
PGPASSWORD=postgres psql -h localhost -p 5432 -d chemlink_analytics <<'SQL'
SELECT 'kratos_identities' AS table, COUNT(*) FROM staging.kratos_identities
UNION ALL
SELECT 'kratos_sessions', COUNT(*) FROM staging.kratos_sessions;
SQL
```

---

### TL;DR
Environment + staging + extraction are complete for Kratos in kube mode. Next sprint is transforming that data into `core`/`aggregates`, adding auth-aware metrics, and documenting verification steps so AI/automation can reason over the full lifecycle (signup → engagement → authentication).***

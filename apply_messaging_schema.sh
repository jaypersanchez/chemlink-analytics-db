#!/bin/bash
# Apply Engagement Platform Messaging Extension Schema to DEV database
# Usage: ./apply_messaging_schema.sh

set -e  # Exit on error

echo "=================================================="
echo "Applying Messaging Extension Schema to DEV"
echo "=================================================="
echo ""

# Database connection settings
DB_HOST="localhost"
DB_PORT="5433"
DB_USER="dev"
DB_NAME="engagement-platform-dev"
export PGPASSWORD="dev"

SCHEMA_FILE="schema/engagement_messaging_extension.sql"

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Error: Schema file not found: $SCHEMA_FILE"
    exit 1
fi

echo "📋 Schema file: $SCHEMA_FILE"
echo "🎯 Target database: $DB_NAME"
echo "🔌 Connection: $DB_HOST:$DB_PORT"
echo ""

# Check if database is accessible
echo "🔍 Checking database connection..."
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to database"
    echo ""
    echo "Make sure:"
    echo "  1. kubectl port-forward is running: chemlink-psql-dev"
    echo "  2. Database exists: engagement-platform-dev"
    exit 1
fi
echo "✅ Database connection OK"
echo ""

# Show existing tables before applying
echo "📊 Current tables in engagement-platform-dev:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt" 2>&1 | grep -E "public \|" || echo "  (none)"
echo ""

# Apply the schema
echo "🚀 Applying messaging extension schema..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $SCHEMA_FILE

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Schema applied successfully!"
    echo ""
    
    # Show new tables
    echo "📊 Updated tables in engagement-platform-dev:"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt" 2>&1 | grep -E "public \|"
    echo ""
    
    # Verify specific tables were created
    echo "🔍 Verifying new tables..."
    TABLES=("conversations" "conversation_participants" "messages" "message_reads" "message_attachments" "message_reactions")
    
    for table in "${TABLES[@]}"; do
        if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\d $table" > /dev/null 2>&1; then
            echo "  ✅ $table"
        else
            echo "  ❌ $table (NOT FOUND)"
        fi
    done
    
    echo ""
    echo "=================================================="
    echo "✅ MESSAGING EXTENSION SCHEMA APPLIED"
    echo "=================================================="
    echo ""
    echo "Tables created:"
    echo "  - conversations"
    echo "  - conversation_participants"
    echo "  - messages"
    echo "  - message_reads"
    echo "  - message_attachments"
    echo "  - message_reactions"
    echo ""
    echo "Next steps:"
    echo "  1. Verify tables: psql -h localhost -p 5433 -U dev -d engagement-platform-dev"
    echo "  2. View schema: \\d conversations"
    echo "  3. Add test data if needed"
    echo ""
else
    echo ""
    echo "❌ Error applying schema"
    exit 1
fi

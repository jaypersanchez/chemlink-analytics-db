# Neo4j Database Exploration Guide

**Purpose:** Probe and understand the schema, relationships, and data structure in Neo4j Aura

**Database:** Neo4j Aura Cloud Instance  
**Access:** https://console-preview.neo4j.io/projects/4c3f0ee2-fee2-4b9a-b83a-cf24f46b7d88/instances

---

## 🎯 Quick Start

Open Neo4j Browser from your Aura console, then run these queries in order.

---

## 📊 1. DISCOVER WHAT'S IN THE DATABASE

### 1.1 List All Node Labels (Like `\dt` in PostgreSQL)

**What it shows:** All types of entities in your graph (User, Post, Company, etc.)

```cypher
CALL db.labels()
```

**Expected output:** List of label names
```
╒═══════════╕
│label      │
╞═══════════╡
│User       │
│Post       │
│Comment    │
│Company    │
└───────────┘
```

---

### 1.2 List All Relationship Types

**What it shows:** All types of connections between nodes (POSTED, FOLLOWS, WORKS_AT, etc.)

```cypher
CALL db.relationshipTypes()
```

**Expected output:** List of relationship type names
```
╒═══════════════════╕
│relationshipType   │
╞═══════════════════╡
│POSTED             │
│COMMENTED_ON       │
│FOLLOWS            │
│WORKS_AT           │
└───────────────────┘
```

---

### 1.3 Count Nodes by Label

**What it shows:** How many nodes of each type exist

```cypher
MATCH (n)
RETURN labels(n) AS NodeType, count(*) AS Count
ORDER BY Count DESC
```

**Expected output:**
```
╒═══════════╤═══════╕
│NodeType   │Count  │
╞═══════════╪═══════╡
│["User"]   │2094   │
│["Post"]   │432    │
│["Comment"]│1205   │
└───────────┴───────┘
```

---

### 1.4 Count Relationships by Type

**What it shows:** How many relationships of each type exist

```cypher
MATCH ()-[r]->()
RETURN type(r) AS RelationshipType, count(*) AS Count
ORDER BY Count DESC
```

**Expected output:**
```
╒═══════════════════╤═══════╕
│RelationshipType   │Count  │
╞═══════════════════╪═══════╡
│COMMENTED_ON       │1205   │
│POSTED             │432    │
│FOLLOWS            │89     │
└───────────────────┴───────┘
```

---

## 🔍 2. INSPECT DATA STRUCTURE

### 2.1 Sample Random Nodes (First 10)

**What it shows:** Actual node data with properties

```cypher
MATCH (n)
RETURN labels(n) AS Labels, 
       properties(n) AS Properties
LIMIT 10
```

**Tip:** This shows what data is stored on each node

---

### 2.2 Show Properties for Specific Node Type

**What it shows:** All property keys used on a specific label

```cypher
MATCH (n:User)  // Change 'User' to any label from step 1.1
RETURN keys(n) AS Properties
LIMIT 1
```

**Example output:**
```
╒═══════════════════════════════════════════╕
│Properties                                 │
╞═══════════════════════════════════════════╡
│["id","email","name","created_at"]        │
└───────────────────────────────────────────┘
```

**Repeat for each label:**
```cypher
// For each label discovered in step 1.1, run:
MATCH (n:Post) RETURN keys(n) LIMIT 1
MATCH (n:Comment) RETURN keys(n) LIMIT 1
MATCH (n:Company) RETURN keys(n) LIMIT 1
// etc.
```

---

### 2.3 Get Full Schema Information (Properties per Label)

**What it shows:** Complete schema with all properties and their types

```cypher
CALL db.schema.nodeTypeProperties()
YIELD nodeType, propertyName, propertyTypes, mandatory
RETURN nodeType, propertyName, propertyTypes, mandatory
ORDER BY nodeType, propertyName
```

**Expected output:**
```
╒════════════╤══════════════╤═══════════════╤═══════════╕
│nodeType    │propertyName  │propertyTypes  │mandatory  │
╞════════════╪══════════════╪═══════════════╪═══════════╡
│(:User)     │id            │["String"]     │false      │
│(:User)     │email         │["String"]     │false      │
│(:User)     │name          │["String"]     │false      │
│(:Post)     │id            │["String"]     │false      │
│(:Post)     │content       │["String"]     │false      │
└────────────┴──────────────┴───────────────┴───────────┘
```

---

### 2.4 Get Relationship Schema (Properties on Relationships)

**What it shows:** Properties stored on relationships (like timestamps, weights, etc.)

```cypher
CALL db.schema.relTypeProperties()
YIELD relType, propertyName, propertyTypes, mandatory
RETURN relType, propertyName, propertyTypes, mandatory
ORDER BY relType, propertyName
```

---

## 🕸️ 3. UNDERSTAND RELATIONSHIP PATTERNS

### 3.1 Show All Relationship Patterns (Which nodes connect to which)

**What it shows:** The graph's connection structure

```cypher
MATCH (a)-[r]->(b)
RETURN DISTINCT
    labels(a)[0] AS FromNode, 
    type(r) AS Relationship, 
    labels(b)[0] AS ToNode,
    count(*) AS Count
ORDER BY Count DESC
```

**Expected output:**
```
╒═══════════╤═══════════════╤═════════╤═══════╕
│FromNode   │Relationship   │ToNode   │Count  │
╞═══════════╪═══════════════╪═════════╪═══════╡
│User       │POSTED         │Post     │432    │
│User       │COMMENTED_ON   │Comment  │1205   │
│User       │FOLLOWS        │User     │89     │
│User       │WORKS_AT       │Company  │2050   │
└───────────┴───────────────┴─────────┴───────┘
```

**This is CRITICAL:** Shows your entire graph structure at a glance!

---

### 3.2 Visualize Sample Relationships

**What it shows:** Visual graph with nodes and edges

```cypher
MATCH (a)-[r]->(b)
RETURN a, r, b
LIMIT 25
```

**Tip:** Neo4j Browser will render this as an interactive graph visualization

---

### 3.3 Find "Hub" Nodes (Most Connected)

**What it shows:** Which nodes have the most relationships

```cypher
MATCH (n)
RETURN labels(n) AS NodeType, 
       n.id AS NodeID,
       n.name AS Name,
       size((n)--()) AS ConnectionCount
ORDER BY ConnectionCount DESC
LIMIT 20
```

**Use case:** Find power users, popular posts, etc.

---

## 🏗️ 4. CHECK DATABASE SETUP

### 4.1 List All Indexes

**What it shows:** Performance optimizations (indexes speed up lookups)

```cypher
CALL db.indexes()
YIELD name, labelsOrTypes, properties, type, state
RETURN name, labelsOrTypes, properties, type, state
```

**Expected output:**
```
╒══════════════╤═══════════════╤═══════════════╤══════════╤════════╕
│name          │labelsOrTypes  │properties     │type      │state   │
╞══════════════╪═══════════════╪═══════════════╪══════════╪════════╡
│user_id_index │["User"]       │["id"]         │BTREE     │ONLINE  │
└──────────────┴───────────────┴───────────────┴──────────┴────────┘
```

---

### 4.2 List All Constraints

**What it shows:** Data integrity rules (uniqueness, existence, etc.)

```cypher
CALL db.constraints()
YIELD name, type, labelsOrTypes, properties
RETURN name, type, labelsOrTypes, properties
```

**Expected output:**
```
╒══════════════════╤════════════╤═══════════════╤═════════════╕
│name              │type        │labelsOrTypes  │properties   │
╞══════════════════╪════════════╪═══════════════╪═════════════╡
│user_id_unique    │UNIQUENESS  │["User"]       │["id"]       │
└──────────────────┴────────────┴───────────────┴─────────────┘
```

---

## 🔬 5. DATA QUALITY CHECKS

### 5.1 Find Orphaned Nodes (No Relationships)

**What it shows:** Nodes that aren't connected to anything

```cypher
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n) AS NodeType, count(*) AS Count
ORDER BY Count DESC
```

**Use case:** Find incomplete data, unused nodes

---

### 5.2 Find Null or Missing Properties

**What it shows:** Data completeness issues

```cypher
MATCH (n:User)  // Change label as needed
WHERE n.email IS NULL OR n.email = ''
RETURN count(*) AS UsersWithoutEmail
```

---

### 5.3 Check Date Ranges (If you have timestamps)

**What it shows:** When data was created/updated

```cypher
MATCH (n)
WHERE n.created_at IS NOT NULL
RETURN 
    labels(n)[0] AS NodeType,
    min(n.created_at) AS OldestRecord,
    max(n.created_at) AS NewestRecord,
    count(*) AS TotalRecords
ORDER BY NodeType
```

---

## 📈 6. SAMPLE DATA QUERIES

### 6.1 Get Sample User with All Relationships

**What it shows:** One user's complete graph neighborhood

```cypher
MATCH (u:User)-[r]-(other)
RETURN u, r, other
LIMIT 50
```

**Use case:** Understand how one entity connects to others

---

### 6.2 Find Specific Patterns (e.g., Users who posted AND commented)

**What it shows:** Complex relationship patterns

```cypher
MATCH (u:User)-[:POSTED]->(p:Post)
MATCH (u)-[:COMMENTED_ON]->(c:Comment)
RETURN u.name AS ActiveUser, 
       count(DISTINCT p) AS PostCount, 
       count(DISTINCT c) AS CommentCount
ORDER BY PostCount + CommentCount DESC
LIMIT 10
```

---

### 6.3 Shortest Path Between Two Nodes

**What it shows:** How entities are connected

```cypher
MATCH (start:User {email: 'user1@example.com'})
MATCH (end:User {email: 'user2@example.com'})
MATCH path = shortestPath((start)-[*]-(end))
RETURN path
```

**Use case:** Find connections, recommendations, influence paths

---

## 🎯 7. EXPORT SCHEMA DOCUMENTATION

### 7.1 Generate Complete Schema Report

**What it shows:** Everything in one query

```cypher
CALL apoc.meta.graph()
YIELD nodes, relationships
RETURN nodes, relationships
```

**Note:** Requires APOC plugin (usually installed on Aura)

---

### 7.2 Alternative: Full Schema Summary

```cypher
CALL db.schema.visualization()
```

**Tip:** Neo4j Browser will show a visual diagram

---

## 🐍 8. PYTHON SCRIPT TO PROBE PROGRAMMATICALLY

Save this as `scripts/probe_neo4j.py`:

```python
#!/usr/bin/env python3
"""
Probe Neo4j database and document schema
"""
from neo4j import GraphDatabase
import json

# TODO: Replace with your Aura credentials
NEO4J_URI = "neo4j+s://your-instance.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your-password"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def probe_database():
    with driver.session() as session:
        print("=" * 70)
        print("NEO4J DATABASE PROBE")
        print("=" * 70)
        
        # 1. Get all labels
        print("\n📋 NODE LABELS:")
        result = session.run("CALL db.labels()")
        labels = [record["label"] for record in result]
        for label in labels:
            print(f"  - {label}")
        
        # 2. Get all relationship types
        print("\n🔗 RELATIONSHIP TYPES:")
        result = session.run("CALL db.relationshipTypes()")
        rel_types = [record["relationshipType"] for record in result]
        for rel_type in rel_types:
            print(f"  - {rel_type}")
        
        # 3. Count nodes by label
        print("\n📊 NODE COUNTS:")
        result = session.run("""
            MATCH (n)
            RETURN labels(n) AS NodeType, count(*) AS Count
            ORDER BY Count DESC
        """)
        for record in result:
            print(f"  {record['NodeType']}: {record['Count']:,}")
        
        # 4. Count relationships by type
        print("\n🔗 RELATIONSHIP COUNTS:")
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS RelType, count(*) AS Count
            ORDER BY Count DESC
        """)
        for record in result:
            print(f"  {record['RelType']}: {record['Count']:,}")
        
        # 5. Relationship patterns
        print("\n🕸️  RELATIONSHIP PATTERNS:")
        result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN DISTINCT
                labels(a)[0] AS FromNode,
                type(r) AS Relationship,
                labels(b)[0] AS ToNode,
                count(*) AS Count
            ORDER BY Count DESC
        """)
        for record in result:
            print(f"  ({record['FromNode']})-[{record['Relationship']}]->({record['ToNode']}): {record['Count']:,}")
        
        # 6. Properties per label
        print("\n📝 PROPERTIES BY NODE TYPE:")
        for label in labels:
            result = session.run(f"""
                MATCH (n:{label})
                RETURN keys(n) AS Properties
                LIMIT 1
            """)
            record = result.single()
            if record:
                props = record['Properties']
                print(f"  {label}: {', '.join(props)}")
        
        print("\n" + "=" * 70)
        print("✅ PROBE COMPLETE")
        print("=" * 70)

if __name__ == '__main__':
    probe_database()
    driver.close()
```

**Run it:**
```bash
cd ~/projects/chemlink-analytics-db
python scripts/probe_neo4j.py
```

---

## 📝 NEXT STEPS

After running these queries:

1. **Document what you find** - Note all labels, relationships, and properties
2. **Understand the data model** - How does it map to your PostgreSQL data?
3. **Design the mapping** - Which PostgreSQL tables should become Neo4j nodes/relationships?
4. **Build ETL script** - Transform PostgreSQL → Neo4j format

---

## 🎯 KEY QUESTIONS TO ANSWER

While probing, answer these:

1. ✅ **What node labels exist?** (from query 1.1)
2. ✅ **What relationship types exist?** (from query 1.2)
3. ✅ **What properties does each node have?** (from query 2.2)
4. ✅ **How are nodes connected?** (from query 3.1)
5. ✅ **Is there existing data or is it empty?** (from query 1.3)
6. ✅ **Are there indexes/constraints?** (from queries 4.1, 4.2)

---

## 📚 REFERENCES

- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Neo4j Browser Guide](https://neo4j.com/docs/browser-manual/current/)
- [APOC Procedures](https://neo4j.com/docs/apoc/current/)

---

**Created:** 2025-11-10  
**Database:** Neo4j Aura Cloud  
**Project:** ChemLink Analytics - Neo4j Integration

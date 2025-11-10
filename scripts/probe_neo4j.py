#!/usr/bin/env python3
"""
Neo4j Database Probe Script

Connects to Neo4j Aura instance and extracts:
- Node labels and counts
- Relationship types and counts
- Properties per node type
- Relationship patterns
- Sample data

Outputs to JSON for analysis and dashboard integration planning.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from neo4j import GraphDatabase

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Neo4j Aura Connection Details
# TODO: Set these as environment variables or in .env
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://your-instance.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your-password")

def log(message, level='INFO'):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {'INFO': '📝', 'SUCCESS': '✅', 'ERROR': '❌', 'WARNING': '⚠️'}
    icon = icons.get(level, '📝')
    print(f"[{timestamp}] {icon} {message}")
    sys.stdout.flush()

class Neo4jProbe:
    """Probe Neo4j database and extract schema/data information"""
    
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.findings = {
            'probe_timestamp': datetime.now().isoformat(),
            'database_uri': uri.split('@')[-1] if '@' in uri else uri,  # Hide credentials
            'labels': [],
            'relationship_types': [],
            'node_counts': {},
            'relationship_counts': {},
            'relationship_patterns': [],
            'node_properties': {},
            'relationship_properties': {},
            'indexes': [],
            'constraints': [],
            'sample_data': {},
            'orphaned_nodes': {},
            'hub_nodes': []
        }
    
    def close(self):
        """Close database connection"""
        self.driver.close()
    
    def run_query(self, query, description):
        """Execute a query and return results"""
        try:
            with self.driver.session() as session:
                result = session.run(query)
                return list(result)
        except Exception as e:
            log(f"Error running {description}: {str(e)}", 'ERROR')
            return []
    
    def probe_labels(self):
        """Get all node labels"""
        log("Fetching node labels...")
        result = self.run_query("CALL db.labels()", "label query")
        self.findings['labels'] = [record['label'] for record in result]
        log(f"  Found {len(self.findings['labels'])} node labels", 'SUCCESS')
    
    def probe_relationship_types(self):
        """Get all relationship types"""
        log("Fetching relationship types...")
        result = self.run_query("CALL db.relationshipTypes()", "relationship type query")
        self.findings['relationship_types'] = [record['relationshipType'] for record in result]
        log(f"  Found {len(self.findings['relationship_types'])} relationship types", 'SUCCESS')
    
    def probe_node_counts(self):
        """Count nodes by label"""
        log("Counting nodes by label...")
        query = """
        MATCH (n)
        RETURN labels(n) AS NodeType, count(*) AS Count
        ORDER BY Count DESC
        """
        result = self.run_query(query, "node count query")
        for record in result:
            label = record['NodeType'][0] if record['NodeType'] else 'Unknown'
            self.findings['node_counts'][label] = record['Count']
        log(f"  Counted {len(self.findings['node_counts'])} node types", 'SUCCESS')
    
    def probe_relationship_counts(self):
        """Count relationships by type"""
        log("Counting relationships by type...")
        query = """
        MATCH ()-[r]->()
        RETURN type(r) AS RelType, count(*) AS Count
        ORDER BY Count DESC
        """
        result = self.run_query(query, "relationship count query")
        for record in result:
            self.findings['relationship_counts'][record['RelType']] = record['Count']
        log(f"  Counted {len(self.findings['relationship_counts'])} relationship types", 'SUCCESS')
    
    def probe_relationship_patterns(self):
        """Get relationship patterns (which nodes connect to which)"""
        log("Analyzing relationship patterns...")
        query = """
        MATCH (a)-[r]->(b)
        RETURN DISTINCT
            labels(a)[0] AS FromNode,
            type(r) AS Relationship,
            labels(b)[0] AS ToNode,
            count(*) AS Count
        ORDER BY Count DESC
        """
        result = self.run_query(query, "relationship pattern query")
        self.findings['relationship_patterns'] = [
            {
                'from': record['FromNode'],
                'relationship': record['Relationship'],
                'to': record['ToNode'],
                'count': record['Count']
            }
            for record in result
        ]
        log(f"  Found {len(self.findings['relationship_patterns'])} relationship patterns", 'SUCCESS')
    
    def probe_node_properties(self):
        """Get properties for each node label"""
        log("Extracting node properties...")
        for label in self.findings['labels']:
            query = f"""
            MATCH (n:{label})
            RETURN keys(n) AS Properties
            LIMIT 1
            """
            result = self.run_query(query, f"{label} properties query")
            if result:
                self.findings['node_properties'][label] = result[0]['Properties']
        log(f"  Extracted properties for {len(self.findings['node_properties'])} node types", 'SUCCESS')
    
    def probe_relationship_properties(self):
        """Get properties for each relationship type"""
        log("Extracting relationship properties...")
        for rel_type in self.findings['relationship_types']:
            query = f"""
            MATCH ()-[r:{rel_type}]->()
            RETURN keys(r) AS Properties
            LIMIT 1
            """
            result = self.run_query(query, f"{rel_type} properties query")
            if result and result[0]['Properties']:
                self.findings['relationship_properties'][rel_type] = result[0]['Properties']
        log(f"  Extracted properties for {len(self.findings['relationship_properties'])} relationship types", 'SUCCESS')
    
    def probe_indexes(self):
        """Get all indexes"""
        log("Fetching indexes...")
        query = """
        CALL db.indexes()
        YIELD name, labelsOrTypes, properties, type, state
        RETURN name, labelsOrTypes, properties, type, state
        """
        result = self.run_query(query, "indexes query")
        self.findings['indexes'] = [
            {
                'name': record['name'],
                'labels_or_types': record['labelsOrTypes'],
                'properties': record['properties'],
                'type': record['type'],
                'state': record['state']
            }
            for record in result
        ]
        log(f"  Found {len(self.findings['indexes'])} indexes", 'SUCCESS')
    
    def probe_constraints(self):
        """Get all constraints"""
        log("Fetching constraints...")
        query = """
        CALL db.constraints()
        YIELD name, type, labelsOrTypes, properties
        RETURN name, type, labelsOrTypes, properties
        """
        result = self.run_query(query, "constraints query")
        self.findings['constraints'] = [
            {
                'name': record['name'],
                'type': record['type'],
                'labels_or_types': record['labelsOrTypes'],
                'properties': record['properties']
            }
            for record in result
        ]
        log(f"  Found {len(self.findings['constraints'])} constraints", 'SUCCESS')
    
    def probe_orphaned_nodes(self):
        """Find nodes with no relationships"""
        log("Finding orphaned nodes...")
        query = """
        MATCH (n)
        WHERE NOT (n)--()
        RETURN labels(n) AS NodeType, count(*) AS Count
        ORDER BY Count DESC
        """
        result = self.run_query(query, "orphaned nodes query")
        for record in result:
            label = record['NodeType'][0] if record['NodeType'] else 'Unknown'
            self.findings['orphaned_nodes'][label] = record['Count']
        log(f"  Found orphaned nodes in {len(self.findings['orphaned_nodes'])} node types", 'SUCCESS')
    
    def probe_hub_nodes(self):
        """Find most connected nodes"""
        log("Finding hub nodes (most connected)...")
        query = """
        MATCH (n)
        WHERE size((n)--()) > 0
        RETURN labels(n) AS NodeType,
               n.id AS NodeID,
               COALESCE(n.name, n.email, n.title, 'N/A') AS Name,
               size((n)--()) AS ConnectionCount
        ORDER BY ConnectionCount DESC
        LIMIT 20
        """
        result = self.run_query(query, "hub nodes query")
        self.findings['hub_nodes'] = [
            {
                'node_type': record['NodeType'][0] if record['NodeType'] else 'Unknown',
                'node_id': record['NodeID'],
                'name': record['Name'],
                'connection_count': record['ConnectionCount']
            }
            for record in result
        ]
        log(f"  Found {len(self.findings['hub_nodes'])} hub nodes", 'SUCCESS')
    
    def probe_sample_data(self):
        """Get sample data for each node type"""
        log("Fetching sample data...")
        for label in self.findings['labels'][:5]:  # Limit to first 5 labels to avoid huge output
            query = f"""
            MATCH (n:{label})
            RETURN properties(n) AS Properties
            LIMIT 3
            """
            result = self.run_query(query, f"{label} sample data query")
            if result:
                self.findings['sample_data'][label] = [record['Properties'] for record in result]
        log(f"  Fetched sample data for {len(self.findings['sample_data'])} node types", 'SUCCESS')
    
    def run_full_probe(self):
        """Execute all probe queries"""
        log("=" * 70)
        log("NEO4J DATABASE PROBE - STARTING")
        log("=" * 70)
        
        try:
            self.probe_labels()
            self.probe_relationship_types()
            self.probe_node_counts()
            self.probe_relationship_counts()
            self.probe_relationship_patterns()
            self.probe_node_properties()
            self.probe_relationship_properties()
            self.probe_indexes()
            self.probe_constraints()
            self.probe_orphaned_nodes()
            self.probe_hub_nodes()
            self.probe_sample_data()
            
            log("=" * 70)
            log("NEO4J DATABASE PROBE - COMPLETE", 'SUCCESS')
            log("=" * 70)
            
            return self.findings
            
        except Exception as e:
            log(f"Probe failed: {str(e)}", 'ERROR')
            import traceback
            log(traceback.format_exc(), 'ERROR')
            return None
    
    def print_summary(self):
        """Print human-readable summary"""
        log("\n" + "=" * 70)
        log("PROBE SUMMARY")
        log("=" * 70)
        
        log(f"\n📋 NODE LABELS ({len(self.findings['labels'])}):")
        for label in self.findings['labels']:
            count = self.findings['node_counts'].get(label, 0)
            log(f"  • {label}: {count:,} nodes")
        
        log(f"\n🔗 RELATIONSHIP TYPES ({len(self.findings['relationship_types'])}):")
        for rel_type in self.findings['relationship_types']:
            count = self.findings['relationship_counts'].get(rel_type, 0)
            log(f"  • {rel_type}: {count:,} relationships")
        
        log(f"\n🕸️  RELATIONSHIP PATTERNS ({len(self.findings['relationship_patterns'])}):")
        for pattern in self.findings['relationship_patterns'][:10]:  # Top 10
            log(f"  • ({pattern['from']})-[{pattern['relationship']}]->({pattern['to']}): {pattern['count']:,}")
        
        log(f"\n📝 NODE PROPERTIES:")
        for label, props in self.findings['node_properties'].items():
            log(f"  • {label}: {', '.join(props)}")
        
        if self.findings['orphaned_nodes']:
            log(f"\n⚠️  ORPHANED NODES:")
            for label, count in self.findings['orphaned_nodes'].items():
                log(f"  • {label}: {count:,} orphaned nodes", 'WARNING')
        
        log(f"\n🌟 TOP HUB NODES (Most Connected):")
        for hub in self.findings['hub_nodes'][:5]:
            log(f"  • {hub['node_type']} '{hub['name']}': {hub['connection_count']} connections")
        
        log("\n" + "=" * 70)

def main():
    """Main execution"""
    
    # Check environment variables
    if NEO4J_URI == "neo4j+s://your-instance.databases.neo4j.io":
        log("⚠️  Neo4j connection details not configured!", 'ERROR')
        log("Set these environment variables:", 'ERROR')
        log("  NEO4J_URI=neo4j+s://your-aura-instance.databases.neo4j.io", 'ERROR')
        log("  NEO4J_USER=neo4j", 'ERROR')
        log("  NEO4J_PASSWORD=your-password", 'ERROR')
        log("\nOr add them to .env file in chemlink-analytics-db/", 'ERROR')
        return 1
    
    # Create probe instance
    log(f"Connecting to Neo4j at {NEO4J_URI.split('@')[-1]}...")
    probe = Neo4jProbe(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # Run probe
        findings = probe.run_full_probe()
        
        if not findings:
            log("Probe failed - no findings returned", 'ERROR')
            return 1
        
        # Print summary to console
        probe.print_summary()
        
        # Save to JSON file
        output_dir = Path(__file__).parent.parent / 'docs'
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / 'neo4j_probe_findings.json'
        
        log(f"\n💾 Saving findings to {output_file}...")
        with open(output_file, 'w') as f:
            json.dump(findings, f, indent=2, default=str)
        
        log(f"✅ Findings saved to {output_file}", 'SUCCESS')
        
        # Also save a formatted report
        report_file = output_dir / 'neo4j_probe_report.md'
        log(f"📄 Generating markdown report at {report_file}...")
        generate_markdown_report(findings, report_file)
        log(f"✅ Report saved to {report_file}", 'SUCCESS')
        
        return 0
        
    except Exception as e:
        log(f"Error during probe: {str(e)}", 'ERROR')
        import traceback
        log(traceback.format_exc(), 'ERROR')
        return 1
    
    finally:
        probe.close()

def generate_markdown_report(findings, output_file):
    """Generate a markdown report from findings"""
    
    with open(output_file, 'w') as f:
        f.write("# Neo4j Database Probe Report\n\n")
        f.write(f"**Generated:** {findings['probe_timestamp']}\n\n")
        f.write(f"**Database:** {findings['database_uri']}\n\n")
        f.write("---\n\n")
        
        # Node labels
        f.write(f"## 📋 Node Labels ({len(findings['labels'])})\n\n")
        for label in findings['labels']:
            count = findings['node_counts'].get(label, 0)
            props = findings['node_properties'].get(label, [])
            f.write(f"### {label}\n")
            f.write(f"- **Count:** {count:,} nodes\n")
            f.write(f"- **Properties:** {', '.join(props) if props else 'None'}\n\n")
        
        # Relationship types
        f.write(f"## 🔗 Relationship Types ({len(findings['relationship_types'])})\n\n")
        for rel_type in findings['relationship_types']:
            count = findings['relationship_counts'].get(rel_type, 0)
            props = findings['relationship_properties'].get(rel_type, [])
            f.write(f"### {rel_type}\n")
            f.write(f"- **Count:** {count:,} relationships\n")
            f.write(f"- **Properties:** {', '.join(props) if props else 'None'}\n\n")
        
        # Relationship patterns
        f.write(f"## 🕸️ Relationship Patterns\n\n")
        f.write("| From Node | Relationship | To Node | Count |\n")
        f.write("|-----------|--------------|---------|-------|\n")
        for pattern in findings['relationship_patterns']:
            f.write(f"| {pattern['from']} | {pattern['relationship']} | {pattern['to']} | {pattern['count']:,} |\n")
        f.write("\n")
        
        # Indexes
        if findings['indexes']:
            f.write(f"## 🏗️ Indexes ({len(findings['indexes'])})\n\n")
            for idx in findings['indexes']:
                f.write(f"- **{idx['name']}**: {idx['labels_or_types']} on {idx['properties']} ({idx['type']}, {idx['state']})\n")
            f.write("\n")
        
        # Constraints
        if findings['constraints']:
            f.write(f"## 🔒 Constraints ({len(findings['constraints'])})\n\n")
            for constraint in findings['constraints']:
                f.write(f"- **{constraint['name']}**: {constraint['type']} on {constraint['labels_or_types']} ({constraint['properties']})\n")
            f.write("\n")
        
        # Orphaned nodes
        if findings['orphaned_nodes']:
            f.write(f"## ⚠️ Orphaned Nodes (No Relationships)\n\n")
            for label, count in findings['orphaned_nodes'].items():
                f.write(f"- **{label}:** {count:,} orphaned nodes\n")
            f.write("\n")
        
        # Hub nodes
        if findings['hub_nodes']:
            f.write(f"## 🌟 Hub Nodes (Most Connected)\n\n")
            f.write("| Node Type | Name | Connections |\n")
            f.write("|-----------|------|-------------|\n")
            for hub in findings['hub_nodes'][:10]:
                f.write(f"| {hub['node_type']} | {hub['name']} | {hub['connection_count']} |\n")
            f.write("\n")

if __name__ == '__main__':
    sys.exit(main())

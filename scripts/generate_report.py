#!/usr/bin/env python3
"""Generate usage reports from the database.

Usage:
    python3 scripts/generate_report.py [options]
    
Options:
    --days N        Look back N days (default: 7)
    --format FORMAT Output format: text, json, csv (default: text)
    --output FILE   Write to file instead of stdout
    
Examples:
    # Text report for last 7 days
    python3 scripts/generate_report.py
    
    # JSON report for last 30 days
    python3 scripts/generate_report.py --days 30 --format json
    
    # CSV export to file
    python3 scripts/generate_report.py --format csv --output report.csv
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.db_explorer import VDBExplorer, AuthDBExplorer


def generate_text_report(days: int) -> str:
    """Generate a human-readable text report."""
    vdb = VDBExplorer()
    auth = AuthDBExplorer()
    
    lines = []
    lines.append("=" * 80)
    lines.append("  📊 SYSTEM USAGE REPORT")
    lines.append("=" * 80)
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Period: Last {days} days")
    lines.append("=" * 80)
    lines.append("")
    
    # Projects and Collections
    lines.append("📦 PROJECTS & COLLECTIONS")
    lines.append("-" * 80)
    projects = vdb.list_projects()
    lines.append(f"  Total Projects: {len(projects)}")
    
    total_collections = 0
    total_vectors = 0
    
    for project in projects[:10]:  # Top 10
        collections = vdb.list_collections(project)
        total_collections += len(collections)
        
        for collection in collections:
            shards = vdb.get_shard_info(project, collection)
            vector_count = sum(s['vector_count'] for s in shards)
            total_vectors += vector_count
    
    lines.append(f"  Total Collections: {total_collections}")
    lines.append(f"  Total Vectors: {total_vectors}")
    lines.append("")
    
    # Users
    lines.append("👥 USERS")
    lines.append("-" * 80)
    user_summary = auth.get_user_summary()
    
    if not user_summary.empty:
        for _, row in user_summary.iterrows():
            lines.append(f"  {row['role']:<15} Total: {row['count']:<3} Active: {row['active_count']}")
    else:
        lines.append("  No user data available")
    
    lines.append("")
    
    # Operations
    lines.append("📈 OPERATIONS")
    lines.append("-" * 80)
    ops = auth.get_operation_summary(days=days)
    
    if not ops.empty:
        # Group by operation
        for op_type in ops['operation_type'].unique():
            op_data = ops[ops['operation_type'] == op_type]
            lines.append(f"  {op_type}")
            for _, row in op_data.iterrows():
                lines.append(f"    {row['status']:<10} {row['count']} operations")
    else:
        lines.append("  No operation data available")
    
    lines.append("")
    
    # API Keys
    lines.append("🔑 API KEYS")
    lines.append("-" * 80)
    keys = auth.get_api_keys(limit=1000)
    
    if not keys.empty:
        active_keys = len(keys[keys['active'] == True]) if 'active' in keys.columns else 0
        revoked_keys = len(keys[keys['revoked'] == True]) if 'revoked' in keys.columns else 0
        lines.append(f"  Total Keys: {len(keys)}")
        lines.append(f"  Active: {active_keys}")
        if 'revoked' in keys.columns:
            lines.append(f"  Revoked: {revoked_keys}")
    else:
        lines.append("  No API key data available")
    
    lines.append("")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def generate_json_report(days: int) -> dict:
    """Generate a machine-readable JSON report."""
    vdb = VDBExplorer()
    auth = AuthDBExplorer()
    
    # Gather data
    projects = vdb.list_projects()
    
    project_data = []
    total_vectors = 0
    
    for project in projects:
        collections = vdb.list_collections(project)
        collection_data = []
        
        for collection in collections:
            shards = vdb.get_shard_info(project, collection)
            vector_count = sum(s['vector_count'] for s in shards)
            total_vectors += vector_count
            
            collection_data.append({
                "name": collection,
                "shards": len(shards),
                "vectors": vector_count
            })
        
        project_data.append({
            "id": project,
            "collections": collection_data
        })
    
    user_summary = auth.get_user_summary()
    users_data = user_summary.to_dict('records') if not user_summary.empty else []
    
    ops = auth.get_operation_summary(days=days)
    ops_data = ops.to_dict('records') if not ops.empty else []
    
    keys = auth.get_api_keys(limit=1000)
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "period_days": days,
        "projects": {
            "total": len(projects),
            "details": project_data
        },
        "vectors": {
            "total": total_vectors
        },
        "users": users_data,
        "operations": ops_data,
        "api_keys": {
            "total": len(keys) if not keys.empty else 0,
            "active": len(keys[keys['active'] == True]) if not keys.empty and 'active' in keys.columns else 0,
            "revoked": len(keys[keys['revoked'] == True]) if not keys.empty and 'revoked' in keys.columns else 0
        }
    }
    
    return report


def generate_csv_report(days: int) -> str:
    """Generate CSV report (operations summary)."""
    auth = AuthDBExplorer()
    ops = auth.get_operation_summary(days=days)
    
    if ops.empty:
        return "operation_type,status,count\n"
    
    return ops.to_csv(index=False)


def main():
    parser = argparse.ArgumentParser(description="Generate usage reports")
    parser.add_argument('--days', type=int, default=7, help='Look back N days')
    parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text')
    parser.add_argument('--output', type=str, help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Generate report
    if args.format == 'text':
        report = generate_text_report(args.days)
    elif args.format == 'json':
        report = json.dumps(generate_json_report(args.days), indent=2)
    else:  # csv
        report = generate_csv_report(args.days)
    
    # Output
    if args.output:
        Path(args.output).write_text(report)
        print(f"✓ Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()

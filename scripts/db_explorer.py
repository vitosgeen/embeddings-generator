#!/usr/bin/env python3
"""Database Explorer - Interactive tool for inspecting VDB and Auth databases.

This script provides an easy way to explore:
- Vector database collections across all shards
- Auth database tables (users, API keys, usage tracking)
- Collection statistics and metadata
"""

import sys
import os
import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import lancedb
    import pyarrow as pa
    HAS_LANCEDB = True
except ImportError:
    HAS_LANCEDB = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Only exit if running as CLI
if __name__ == "__main__" and not (HAS_LANCEDB and HAS_PANDAS):
    print("Error: Required packages not installed.")
    print("Run: pip install lancedb pyarrow pandas")
    sys.exit(1)


class VDBExplorer:
    """Explorer for Vector Database."""
    
    def __init__(self, vdb_path: str = "./vdb-data"):
        self.vdb_path = Path(vdb_path)
        
    def list_projects(self) -> List[str]:
        """List all projects."""
        if not self.vdb_path.exists():
            return []
        
        projects = []
        for item in self.vdb_path.iterdir():
            if item.is_dir() and (item / "collections").exists():
                projects.append(item.name)
        return sorted(projects)
    
    def list_collections(self, project_id: str) -> List[str]:
        """List all collections in a project."""
        collections_path = self.vdb_path / project_id / "collections"
        if not collections_path.exists():
            return []
        
        collections = []
        for item in collections_path.iterdir():
            if item.is_dir() and (item / "_config.json").exists():
                collections.append(item.name)
        return sorted(collections)
    
    def get_collection_config(self, project_id: str, collection: str) -> Optional[Dict]:
        """Get collection configuration."""
        config_path = self.vdb_path / project_id / "collections" / collection / "_config.json"
        if not config_path.exists():
            return None
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def get_shard_info(self, project_id: str, collection: str) -> List[Dict]:
        """Get information about all shards in a collection."""
        collection_path = self.vdb_path / project_id / "collections" / collection
        config = self.get_collection_config(project_id, collection)
        
        if not config:
            return []
        
        shard_info = []
        for shard_id in range(config['shards']):
            shard_path = collection_path / f"shard_{shard_id}"
            
            info = {
                "shard_id": shard_id,
                "path": str(shard_path),
                "exists": shard_path.exists(),
                "vector_count": 0,
                "has_table": False
            }
            
            if shard_path.exists():
                table_path = shard_path / "vectors.lance"
                info["has_table"] = table_path.exists()
                
                if info["has_table"]:
                    try:
                        db = lancedb.connect(str(shard_path))
                        table = db.open_table("vectors")
                        info["vector_count"] = table.count_rows()
                    except Exception as e:
                        info["error"] = str(e)
            
            shard_info.append(info)
        
        return shard_info
    
    def get_vectors(self, project_id: str, collection: str, shard_id: int, 
                   limit: int = 10, include_vectors: bool = False):
        """Get vectors from a specific shard.
        
        Returns:
            - pd.DataFrame if pandas is available
            - List[Dict] if pandas is not available
        """
        shard_path = self.vdb_path / project_id / "collections" / collection / f"shard_{shard_id}"
        
        if not shard_path.exists():
            return pd.DataFrame() if HAS_PANDAS else []
        
        try:
            db = lancedb.connect(str(shard_path))
            table = db.open_table("vectors")
            
            # Get data as arrow table
            arrow_table = table.to_arrow()
            
            # Limit rows
            if limit:
                arrow_table = arrow_table.slice(0, min(limit, arrow_table.num_rows))
            
            # Convert to list of dicts
            rows = arrow_table.to_pylist()
            
            # Process rows
            for row in rows:
                # Handle vector column
                if 'vector' in row:
                    if include_vectors:
                        # Keep vector as list
                        pass
                    else:
                        # Replace with dimension info
                        row['vector_dim'] = len(row['vector']) if row['vector'] else 0
                        del row['vector']
                
                # Parse metadata JSON
                if 'metadata' in row and isinstance(row['metadata'], str):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except:
                        pass
            
            # Return pandas DataFrame if available, otherwise list
            if HAS_PANDAS:
                return pd.DataFrame(rows)
            else:
                return rows
                
        except Exception as e:
            print(f"Error reading shard {shard_id}: {e}")
            return pd.DataFrame() if HAS_PANDAS else []
    
    def search_by_id(self, project_id: str, collection: str, vector_id: str) -> Optional[Dict]:
        """Search for a vector by ID across all shards."""
        config = self.get_collection_config(project_id, collection)
        if not config:
            return None
        
        # Calculate which shard should contain this ID
        import hashlib
        hash_value = int(hashlib.md5(vector_id.encode()).hexdigest(), 16)
        shard_id = hash_value % config['shards']
        
        shard_path = self.vdb_path / project_id / "collections" / collection / f"shard_{shard_id}"
        
        if not shard_path.exists():
            return None
        
        try:
            db = lancedb.connect(str(shard_path))
            table = db.open_table("vectors")
            
            # Use PyArrow filter
            import pyarrow.compute as pc
            arrow_table = table.to_arrow()
            mask = pc.equal(arrow_table['id'], vector_id)
            filtered = arrow_table.filter(mask)
            
            if filtered.num_rows == 0:
                return None
            
            row = filtered.to_pylist()[0]
            row['metadata'] = json.loads(row.get('metadata', '{}'))
            row['vector_dim'] = len(row.get('vector', []))
            row['shard_id'] = shard_id
            
            return row
        except Exception as e:
            print(f"Error searching for {vector_id}: {e}")
            return None


class AuthDBExplorer:
    """Explorer for Authentication Database."""
    
    def __init__(self, db_path: str = "./data/auth.db"):
        self.db_path = Path(db_path)
    
    def _execute(self, query: str) -> List[Dict]:
        """Execute a query and return results as list of dicts."""
        if not self.db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
    
    def list_tables(self) -> List[str]:
        """List all tables in auth database."""
        results = self._execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r['name'] for r in results]
    
    def get_users(self, limit: int = 100) -> pd.DataFrame:
        """Get all users."""
        results = self._execute(f"SELECT * FROM users LIMIT {limit}")
        return pd.DataFrame(results)
    
    def get_api_keys(self, limit: int = 100) -> pd.DataFrame:
        """Get all API keys."""
        results = self._execute(
            f"SELECT key_id, user_id, label, active, revoked, created_at, expires_at "
            f"FROM api_keys ORDER BY created_at DESC LIMIT {limit}"
        )
        return pd.DataFrame(results)
    
    def get_usage_stats(self, limit: int = 100) -> pd.DataFrame:
        """Get recent usage tracking."""
        results = self._execute(
            f"SELECT * FROM usage_tracking ORDER BY timestamp DESC LIMIT {limit}"
        )
        df = pd.DataFrame(results)
        
        # Parse metadata JSON
        if not df.empty and 'metadata' in df.columns:
            df['metadata'] = df['metadata'].apply(
                lambda x: json.loads(x) if x else {}
            )
        
        return df
    
    def get_user_summary(self) -> pd.DataFrame:
        """Get summary of users by role."""
        results = self._execute(
            "SELECT role, COUNT(*) as count, "
            "SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) as active_count "
            "FROM users GROUP BY role"
        )
        return pd.DataFrame(results)
    
    def get_operation_summary(self, days: int = 7) -> pd.DataFrame:
        """Get operation summary for last N days."""
        results = self._execute(
            f"SELECT operation_type, status, COUNT(*) as count "
            f"FROM usage_tracking "
            f"WHERE timestamp >= datetime('now', '-{days} days') "
            f"GROUP BY operation_type, status "
            f"ORDER BY count DESC"
        )
        return pd.DataFrame(results)


def print_table(df: pd.DataFrame, title: str = None, max_width: int = 120):
    """Print a formatted table."""
    if title:
        print(f"\n{'='*max_width}")
        print(f"  {title}")
        print(f"{'='*max_width}")
    
    if df.empty:
        print("  (No data)")
        return
    
    # Format output
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', max_width)
    pd.set_option('display.max_colwidth', 50)
    
    print(df.to_string(index=False))
    print(f"\nTotal rows: {len(df)}")


def interactive_menu():
    """Interactive menu for database exploration."""
    vdb = VDBExplorer()
    auth = AuthDBExplorer()
    
    while True:
        print("\n" + "="*80)
        print("  🔍 DATABASE EXPLORER")
        print("="*80)
        print("\n📊 Vector Database:")
        print("  1. List all projects")
        print("  2. List collections in a project")
        print("  3. View collection info and shards")
        print("  4. View vectors in a shard")
        print("  5. Search vector by ID")
        print("\n👥 Auth Database:")
        print("  6. View users")
        print("  7. View API keys")
        print("  8. View recent usage")
        print("  9. View user summary")
        print("  10. View operation statistics")
        print("\n  0. Exit")
        print("-"*80)
        
        try:
            choice = input("Select option: ").strip()
            
            if choice == '0':
                print("\n👋 Goodbye!")
                break
            
            elif choice == '1':
                projects = vdb.list_projects()
                print_table(pd.DataFrame({"Projects": projects}), "All Projects")
            
            elif choice == '2':
                project = input("Enter project ID: ").strip()
                collections = vdb.list_collections(project)
                print_table(pd.DataFrame({"Collections": collections}), 
                          f"Collections in '{project}'")
            
            elif choice == '3':
                project = input("Enter project ID: ").strip()
                collection = input("Enter collection name: ").strip()
                
                config = vdb.get_collection_config(project, collection)
                if config:
                    print(f"\n📋 Collection Config:")
                    print(f"  Name: {config.get('name')}")
                    print(f"  Dimension: {config.get('dimension')}")
                    print(f"  Metric: {config.get('metric')}")
                    print(f"  Shards: {config.get('shards')}")
                    print(f"  Created: {config.get('created_at')}")
                
                shards = vdb.get_shard_info(project, collection)
                print_table(pd.DataFrame(shards), "Shard Information")
            
            elif choice == '4':
                project = input("Enter project ID: ").strip()
                collection = input("Enter collection name: ").strip()
                shard = int(input("Enter shard ID: ").strip())
                limit = int(input("Limit (default 10): ").strip() or "10")
                
                df = vdb.get_vectors(project, collection, shard, limit=limit)
                print_table(df, f"Vectors in Shard {shard}")
            
            elif choice == '5':
                project = input("Enter project ID: ").strip()
                collection = input("Enter collection name: ").strip()
                vector_id = input("Enter vector ID: ").strip()
                
                result = vdb.search_by_id(project, collection, vector_id)
                if result:
                    print(f"\n✓ Found in shard {result['shard_id']}:")
                    print(f"  ID: {result['id']}")
                    print(f"  Document: {result.get('document', 'N/A')[:100]}")
                    print(f"  Metadata: {result.get('metadata')}")
                    print(f"  Vector dimension: {result.get('vector_dim')}")
                    print(f"  Created: {result.get('created_at')}")
                    print(f"  Deleted: {result.get('deleted', False)}")
                else:
                    print("\n✗ Vector not found")
            
            elif choice == '6':
                limit = int(input("Limit (default 100): ").strip() or "100")
                df = auth.get_users(limit=limit)
                print_table(df, "Users")
            
            elif choice == '7':
                limit = int(input("Limit (default 100): ").strip() or "100")
                df = auth.get_api_keys(limit=limit)
                print_table(df, "API Keys")
            
            elif choice == '8':
                limit = int(input("Limit (default 100): ").strip() or "100")
                df = auth.get_usage_stats(limit=limit)
                print_table(df, "Recent Usage")
            
            elif choice == '9':
                df = auth.get_user_summary()
                print_table(df, "User Summary by Role")
            
            elif choice == '10':
                days = int(input("Days to look back (default 7): ").strip() or "7")
                df = auth.get_operation_summary(days=days)
                print_table(df, f"Operations (Last {days} Days)")
            
            else:
                print("\n❌ Invalid option")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting Database Explorer...")
    
    # Check if databases exist
    vdb_path = Path("./vdb-data")
    auth_path = Path("./data/auth.db")
    
    if not vdb_path.exists():
        print(f"⚠️  Warning: VDB path not found at {vdb_path}")
    
    if not auth_path.exists():
        print(f"⚠️  Warning: Auth DB not found at {auth_path}")
    
    interactive_menu()

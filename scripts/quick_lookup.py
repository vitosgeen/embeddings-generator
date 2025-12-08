#!/usr/bin/env python3
"""Quick vector lookup utility.

Usage:
    python3 scripts/quick_lookup.py <project_id> <collection> <vector_id>
    
Example:
    python3 scripts/quick_lookup.py simple_test docs doc1
"""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.db_explorer import VDBExplorer


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 scripts/quick_lookup.py <project_id> <collection> <vector_id>")
        print("\nExample:")
        print("  python3 scripts/quick_lookup.py simple_test docs doc1")
        sys.exit(1)
    
    project_id = sys.argv[1]
    collection = sys.argv[2]
    vector_id = sys.argv[3]
    
    vdb = VDBExplorer()
    
    print(f"🔍 Searching for vector '{vector_id}' in {project_id}/{collection}...")
    print()
    
    result = vdb.search_by_id(project_id, collection, vector_id)
    
    if result:
        print(f"✓ Found in shard {result['shard_id']}")
        print("─" * 80)
        print(f"📝 ID:        {result['id']}")
        print(f"📄 Document:  {result.get('document', 'N/A')[:200]}")
        if len(result.get('document', '')) > 200:
            print(f"              ... ({len(result.get('document', ''))} characters total)")
        print(f"🏷️  Metadata:  {json.dumps(result.get('metadata'), indent=2)}")
        print(f"📊 Vector:    {result.get('vector_dim')} dimensions")
        print(f"📅 Created:   {result.get('created_at')}")
        print(f"📅 Updated:   {result.get('updated_at')}")
        print(f"🗑️  Deleted:   {result.get('deleted', False)}")
        print("─" * 80)
    else:
        print(f"✗ Vector '{vector_id}' not found in {project_id}/{collection}")
        print()
        print("💡 Tips:")
        print("  - Check that the project and collection names are correct")
        print("  - Use 'python3 scripts/db_explorer.py' to browse all data")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Database Explorer

An interactive tool for inspecting Vector Database and Authentication Database with automatic shard handling.

## Features

### 🔍 Vector Database Explorer
- **List Projects**: View all projects in your VDB
- **List Collections**: View collections within a project
- **Collection Info**: See configuration and shard distribution
- **View Vectors**: Browse vectors in any shard (handles sharding automatically)
- **Search by ID**: Find vectors by ID (automatically calculates correct shard)

### 👥 Auth Database Explorer
- **Users**: View all users and their roles
- **API Keys**: Inspect API keys and their status
- **Usage Tracking**: See recent API usage
- **User Summary**: Statistics grouped by role
- **Operation Stats**: Operation counts and success rates

## Quick Start

```bash
# Run the interactive explorer
python3 scripts/db_explorer.py

# Or make it executable and run directly
chmod +x scripts/db_explorer.py
./scripts/db_explorer.py

# Quick vector lookup (command-line)
python3 scripts/quick_lookup.py simple_test docs doc1

# Run the demo
./scripts/demo_explorer.sh
```

## Usage Examples

### Exploring Vector Data

```
Select option: 1
# Lists all projects (e.g., simple_test, my_project)

Select option: 2
Enter project ID: simple_test
# Lists all collections (e.g., docs, articles)

Select option: 3
Enter project ID: simple_test
Enter collection name: docs
# Shows configuration and shard information:
#   Name: docs
#   Dimension: 768
#   Shards: 4
#   Shard 0: 3 vectors
#   Shard 1: 0 vectors
#   Shard 2: 1 vectors
#   Shard 3: 0 vectors

Select option: 4
Enter project ID: simple_test
Enter collection name: docs
Enter shard ID: 0
Limit: 10
# Shows vectors in shard 0 with metadata
```

### Finding Specific Vector

```
Select option: 5
Enter project ID: simple_test
Enter collection name: docs
Enter vector ID: doc1
# Automatically finds the correct shard and displays:
#   ✓ Found in shard 0:
#   ID: doc1
#   Document: Python is a powerful programming language...
#   Metadata: {'category': 'programming', 'level': 'beginner'}
#   Vector dimension: 768
#   Created: 2024-12-08 15:30:00
```

### Checking Usage Statistics

```
Select option: 8
Limit: 50
# Shows recent API usage:
#   operation_type | status | user_id | project_id | timestamp
#   simple_search  | success| admin  | simple_test| 2024-12-08 16:00:00
#   simple_add_text| success| admin  | simple_test| 2024-12-08 15:55:00

Select option: 10
Days to look back: 7
# Shows operation summary:
#   operation_type    | status  | count
#   simple_add_text   | success | 145
#   simple_search_text| success | 89
#   generate_embedding| success | 67
```

## Why This Tool?

### Problem: Sharding Makes Direct Inspection Difficult
- Vectors are distributed across multiple shards using hash-based sharding
- Tools like DB Browser for SQLite or DBeaver don't understand the sharding logic
- You'd have to manually calculate which shard contains a specific vector ID

### Solution: Automatic Shard Handling
- **Smart ID Lookup**: Automatically calculates the correct shard for any vector ID
- **Unified View**: Browse all data through a single interface
- **Metadata Parsing**: Automatically parses JSON metadata fields
- **Usage Analytics**: Built-in statistics and summaries

## Features Details

### Vector Dimension Handling
- By default, vector values are hidden (they're large arrays)
- Shows `vector_dim` instead (e.g., 768, 1024)
- Use `include_vectors=True` in code if you need actual values

### Metadata Display
- Automatically parses JSON metadata into Python dicts
- Pretty-prints nested structures
- Shows empty dict `{}` if no metadata

### Shard Distribution
- Shows which shards have data and how many vectors
- Helps identify load balancing across shards
- Useful for troubleshooting missing data

### Usage Tracking
- See which operations are most used
- Check success/failure rates
- Monitor quota consumption per user

## Advanced Usage

### Programmatic Access

```python
from scripts.db_explorer import VDBExplorer, AuthDBExplorer

# Vector DB
vdb = VDBExplorer("./vdb-data")
projects = vdb.list_projects()
print(projects)  # ['simple_test', 'my_project']

collections = vdb.list_collections("simple_test")
print(collections)  # ['docs', 'articles']

# Get vectors as DataFrame
df = vdb.get_vectors("simple_test", "docs", shard_id=0, limit=100)
print(df.head())

# Search by ID
vector = vdb.search_by_id("simple_test", "docs", "doc1")
print(vector['metadata'])

# Auth DB
auth = AuthDBExplorer("./data/auth.db")

# Get users
users_df = auth.get_users(limit=50)
print(users_df)

# Get usage stats
usage_df = auth.get_usage_stats(limit=100)
print(usage_df[usage_df['status'] == 'error'])  # Show only errors
```

### Filtering and Analysis

```python
import pandas as pd
from scripts.db_explorer import AuthDBExplorer

auth = AuthDBExplorer()

# Get all usage data
df = auth.get_usage_stats(limit=1000)

# Find slow operations
slow_ops = df[df['metadata'].apply(lambda x: x.get('duration_ms', 0) > 1000)]
print(f"Slow operations: {len(slow_ops)}")

# Operations by user
user_ops = df.groupby('user_id')['operation_type'].value_counts()
print(user_ops)

# Error rate by operation
error_rate = df.groupby('operation_type')['status'].apply(
    lambda x: (x == 'error').sum() / len(x) * 100
)
print(f"Error rates:\n{error_rate}")
```

## Troubleshooting

### "No data" when viewing collection
- Check that vectors were actually added
- Verify correct project and collection names
- Use option 3 to see shard distribution

### "Vector not found" when searching by ID
- Ensure the ID exists (check with option 4)
- Verify project and collection names are correct
- The tool automatically handles sharding, so this means the vector truly doesn't exist

### Empty usage tracking
- Ensure the service has been running and processing requests
- Check that auth database path is correct (`./data/auth.db`)
- Usage is only tracked for authenticated requests

## Integration with Development Workflow

```bash
# Quick lookup during development
python3 scripts/quick_lookup.py my_project documents doc123

# After adding test data
python3 scripts/db_explorer.py
# Select option 4 to verify data was added correctly

# After running tests
python3 scripts/db_explorer.py
# Select option 10 to see operation statistics

# For debugging search issues
python3 scripts/db_explorer.py
# Select option 5 to find the specific vector and check its content

# Run the full demo
./scripts/demo_explorer.sh
```

## Performance Notes

- Reading from LanceDB shards is fast (columnar storage)
- Large collections: Use limit parameter to avoid loading too much data
- Vector arrays are excluded by default to keep memory usage low
- Metadata JSON parsing happens on-the-fly

## Future Enhancements

Potential additions:
- Export functionality (CSV, JSON)
- Bulk operations (delete, update metadata)
- Vector similarity visualization
- Real-time monitoring mode
- Web-based UI version

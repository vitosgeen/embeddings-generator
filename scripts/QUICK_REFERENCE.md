# 🔍 Database Explorer - Quick Reference

## Launch Commands

```bash
# Interactive menu
python3 scripts/db_explorer.py

# Quick vector lookup
python3 scripts/quick_lookup.py <project> <collection> <id>

# Demo
./scripts/demo_explorer.sh
```

## Menu Options

### 📊 Vector Database (1-5)

| Option | Action | Example |
|--------|--------|---------|
| **1** | List all projects | Shows: simple_test, my_project, demo_project... |
| **2** | List collections | Input: simple_test → Shows: docs, articles... |
| **3** | Collection info & shards | Shows config + shard distribution |
| **4** | View vectors in shard | Browse actual vector data |
| **5** | Search vector by ID | Auto-finds correct shard |

### 👥 Auth Database (6-10)

| Option | Action | What You See |
|--------|--------|-------------|
| **6** | View users | User list with roles, status |
| **7** | View API keys | Keys with labels, expiry |
| **8** | Recent usage | Last N operations |
| **9** | User summary | Count by role |
| **10** | Operation stats | Success/error rates |

## Common Workflows

### 🔎 Find a Specific Vector
```bash
# Method 1: Quick lookup
python3 scripts/quick_lookup.py simple_test docs doc1

# Method 2: Interactive
python3 scripts/db_explorer.py
5 → simple_test → docs → doc1
```

### 📈 Check System Usage
```bash
python3 scripts/db_explorer.py
9  # User summary by role
10 # Operation statistics (last 7 days)
```

### 🐛 Debug "Vector Not Found"
```bash
# Verify the vector exists
python3 scripts/quick_lookup.py my_project docs missing_doc
# Shows: ✗ Vector not found (confirms it's missing)

# Check shard distribution
python3 scripts/db_explorer.py
3 → my_project → docs
# Shows which shards have data
```

### 📊 View Collection Statistics
```bash
python3 scripts/db_explorer.py
3 → simple_test → docs
# Shows:
#   Dimension: 768
#   Shards: 4
#   Shard 0: 2 vectors
#   Shard 2: 1 vector
#   Total: 3 vectors
```

## Keyboard Shortcuts

- **Enter menu option**: Type number + Enter
- **Exit**: Type `0` or `Ctrl+C`
- **Cancel input**: `Ctrl+C` (returns to menu)

## Quick Tips

### 💡 Viewing Large Collections
```
Limit (default 10): 100  ← Enter higher number
```

### 💡 Understanding Shards
- Vectors distributed via MD5 hash: `hash(id) % num_shards`
- Explorer calculates automatically
- Empty shards are normal (not all hashes map to each shard)

### 💡 Metadata Display
- JSON parsed automatically
- Shows formatted dicts
- Empty if no metadata: `{}`

### 💡 Vector Arrays
- Hidden by default (too large: 768-1024 floats)
- Shows dimensions instead: `vector_dim: 768`
- Use programmatic access if you need actual values

## Output Examples

### Vector Search Result
```
✓ Found in shard 0:
  ID:        doc1
  Document:  Python is a powerful programming language...
  Metadata:  {'category': 'programming', 'level': 'beginner'}
  Vector:    768 dimensions
  Created:   1765051411
  Deleted:   False
```

### Shard Distribution
```
shard_id | path                                    | vector_count | has_table
---------|----------------------------------------|--------------|----------
0        | vdb-data/simple_test/.../shard_0       | 2            | True
1        | vdb-data/simple_test/.../shard_1       | 0            | False
2        | vdb-data/simple_test/.../shard_2       | 1            | True
3        | vdb-data/simple_test/.../shard_3       | 1            | True
```

### User Summary
```
role          | count | active_count
--------------|-------|-------------
admin         | 1     | 1
project-owner | 1     | 1
monitor       | 2     | 2
service-app   | 2     | 2
```

### Operation Statistics
```
operation_type    | status  | count
-----------------|---------|------
simple_add_text   | success | 145
simple_search_text| success | 89
generate_embedding| success | 67
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No data" in collections | Check option 1 (list projects) first |
| Vector not found | Verify project/collection names are correct |
| Empty usage tracking | Table may not exist yet or no operations recorded |
| Import errors | Install: `pip install lancedb pyarrow pandas` |

## Programmatic Usage

```python
from scripts.db_explorer import VDBExplorer, AuthDBExplorer

# Vector DB
vdb = VDBExplorer()
projects = vdb.list_projects()
vector = vdb.search_by_id("simple_test", "docs", "doc1")

# Auth DB  
auth = AuthDBExplorer()
users_df = auth.get_users(limit=100)
stats_df = auth.get_operation_summary(days=7)
```

## File Locations

```
scripts/
├── db_explorer.py          # Main tool
├── quick_lookup.py         # CLI lookup
├── demo_explorer.sh        # Demo script
├── README_EXPLORER.md      # Full docs
└── QUICK_REFERENCE.md      # This file
```

## Help & Documentation

- **Full docs**: `scripts/README_EXPLORER.md`
- **Implementation**: `docs/DATABASE_EXPLORER.md`
- **Main README**: See "Database Explorer Tool" section
- **Support**: Create GitHub issue

---

**Pro Tip**: Bookmark this file for quick reference! 🔖

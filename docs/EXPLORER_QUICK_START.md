# Database Explorer - Quick Start Guide

## 🌐 Web Interface (Easiest)

### Step 1: Access the Explorer
1. Start the service: `python3 main.py`
2. Open browser: `http://localhost:8000/admin/`
3. Login with admin credentials
4. Click **"🔍 DB Explorer"** in navigation menu

### Step 2: Browse Projects
- **Projects Tab** (default view):
  - See all projects listed with stats
  - Shows: collection count, total vectors
  - Click any project to see details

**What you'll see**:
```
📦 All Projects

simple_test
  2 collections • 4 vectors
  
my_project  
  1 collections • 15 vectors

demo_project
  3 collections • 50 vectors
```

### Step 3: View Collection Details
- Click any project name
- Modal popup shows:
  - Collection name, dimension, metric
  - Number of shards
  - Total vectors
  - **Shard distribution** (visual grid)

**Example**:
```
Project: simple_test

Collection: docs
  Dimension: 768
  Metric: cosine
  Shards: 4
  Total Vectors: 4

Shard Distribution:
┌──────────┬──────────┬──────────┬──────────┐
│ Shard 0  │ Shard 1  │ Shard 2  │ Shard 3  │
│    2     │    0     │    1     │    1     │
│  (green) │  (gray)  │ (green)  │ (green)  │
└──────────┴──────────┴──────────┴──────────┘
```

### Step 4: Search for Vectors
- Click **"🔎 Search Vector"** tab
- Fill in form:
  - **Project ID**: e.g., `simple_test`
  - **Collection**: e.g., `docs`
  - **Vector ID**: e.g., `doc1`
- Click **"🔍 Search Vector"** button

**Result**:
```
✓ Found in shard 0

ID: doc1
Document: Python is a powerful programming language...
Metadata: {"category": "programming", "level": "beginner"}
Vector Dimension: 768 dimensions
Created: 12/8/2025, 10:23:31 AM
```

### Step 5: View Auth Statistics
- Click **"👥 Auth Database"** tab
- See two tables:
  1. **User Statistics**: Users grouped by role
  2. **Operation Statistics**: Last 7 days of operations

**Example**:
```
User Statistics
┌───────────────┬─────────────┬──────────────┐
│ Role          │ Total Users │ Active Users │
├───────────────┼─────────────┼──────────────┤
│ admin         │      1      │      1       │
│ project-owner │      1      │      1       │
│ monitor       │      2      │      2       │
└───────────────┴─────────────┴──────────────┘

Operation Statistics (Last 7 Days)
┌─────────────────┬─────────┬───────┐
│ Operation       │ Status  │ Count │
├─────────────────┼─────────┼───────┤
│ simple_add_text │ success │  145  │
│ simple_search   │ success │   89  │
│ generate_embed  │ success │   67  │
└─────────────────┴─────────┴───────┘
```

## 💻 CLI Interface (For Scripts)

### Quick Lookup
Fastest way to find a specific vector:

```bash
python3 scripts/quick_lookup.py simple_test docs doc1
```

**Output**:
```
🔍 Searching for vector 'doc1' in simple_test/docs...

✓ Found in shard 0
────────────────────────────────────────────────────────
📝 ID:        doc1
📄 Document:  Python is a powerful programming language...
🏷️  Metadata:  {"category": "programming", "level": "beginner"}
📊 Vector:    768 dimensions
📅 Created:   1765051411
🗑️  Deleted:   False
────────────────────────────────────────────────────────
```

### Interactive Menu
Full-featured CLI explorer:

```bash
python3 scripts/db_explorer.py
```

**Menu Options**:
```
🔍 DATABASE EXPLORER

📊 Vector Database:
  1. List all projects
  2. List collections in a project
  3. View collection info and shards
  4. View vectors in a shard
  5. Search vector by ID

👥 Auth Database:
  6. View users
  7. View API keys
  8. View recent usage
  9. View user summary
  10. View operation statistics

  0. Exit
```

**Common Workflows**:

1. **Browse data**:
   ```
   Select option: 1  (list projects)
   Select option: 2  (list collections)
   Enter project ID: simple_test
   Select option: 3  (view collection details)
   Enter project ID: simple_test
   Enter collection name: docs
   ```

2. **Find vector**:
   ```
   Select option: 5
   Enter project ID: simple_test
   Enter collection name: docs
   Enter vector ID: doc1
   ```

3. **Check usage**:
   ```
   Select option: 9  (user summary)
   Select option: 10 (operation stats)
   Days to look back: 7
   ```

### Generate Reports
Create formatted reports:

```bash
# Text report (human-readable)
python3 scripts/generate_report.py

# JSON report (machine-readable)
python3 scripts/generate_report.py --format json --days 30

# CSV export
python3 scripts/generate_report.py --format csv --output report.csv
```

## 🎯 Use Cases

### 1. Verify Data After Upload
**Scenario**: You just added documents via Simple API

**Web**:
1. Go to DB Explorer → Projects tab
2. Click your project
3. Check shard distribution shows new vectors

**CLI**:
```bash
python3 scripts/quick_lookup.py my_project docs new_doc_id
```

### 2. Debug "Vector Not Found" Error
**Scenario**: API says vector doesn't exist

**Web**:
1. Go to Search Vector tab
2. Enter project, collection, vector ID
3. See if it's really missing or in different shard

**CLI**:
```bash
python3 scripts/quick_lookup.py project1 coll1 missing_doc
# Either shows the vector or confirms it's missing
```

### 3. Monitor System Usage
**Scenario**: Check which operations are most used

**Web**:
1. Go to Auth Database tab
2. View Operation Statistics table
3. See counts by operation type

**CLI**:
```bash
python3 scripts/db_explorer.py
# Select option: 10 (operation statistics)
# Days to look back: 7
```

### 4. Check Shard Distribution
**Scenario**: Ensure vectors are balanced across shards

**Web**:
1. Browse to project
2. Click project name
3. Visual grid shows distribution

**CLI**:
```bash
python3 scripts/db_explorer.py
# Select option: 3 (collection info)
# Shows table with vector count per shard
```

## 🔑 Key Features

### Web Interface
✅ **No installation**: Works in any browser
✅ **Visual**: Color-coded, formatted tables
✅ **Interactive**: Click to explore
✅ **Integrated**: Same auth as admin dashboard
✅ **Fast**: AJAX requests, no page reloads

### CLI Interface
✅ **Scriptable**: Easy to automate
✅ **Fast**: Direct Python access
✅ **Flexible**: Multiple output formats
✅ **Portable**: Works on any system with Python

## 💡 Tips & Tricks

### Web Interface
- **Keyboard shortcut**: Bookmark `http://localhost:8000/admin/explorer`
- **Multiple searches**: Results stay visible until next search
- **Modal close**: Click outside or X button to close project details
- **Tab navigation**: Click tab names or use keyboard

### CLI Interface
- **Exit anytime**: Press `Ctrl+C` or select option 0
- **Large collections**: Use limit parameter (e.g., 100 instead of default 10)
- **Quick re-run**: Use arrow keys to recall previous commands
- **Batch lookup**: Create shell script with multiple lookups

### Reports
- **JSON output**: Pipe to `jq` for formatting: `... | jq .`
- **CSV import**: Open in Excel, Google Sheets, or pandas
- **Automation**: Add to cron for daily reports
- **Comparison**: Generate weekly reports to track growth

## 🆘 Troubleshooting

### Web Interface

**Problem**: Page shows "Please login"
**Solution**: Login to admin dashboard first at `/admin/login`

**Problem**: Projects tab empty
**Solution**: Check that `./vdb-data/` directory exists and has data

**Problem**: Search says "Vector not found"
**Solution**: Verify project ID, collection name, and vector ID are correct (case-sensitive)

### CLI Interface

**Problem**: Import error for `lancedb`
**Solution**: `pip install lancedb pyarrow pandas`

**Problem**: "No data" when viewing collection
**Solution**: Use option 1 to list projects first, verify names

**Problem**: Permission denied
**Solution**: Make script executable: `chmod +x scripts/db_explorer.py`

## 📚 Documentation

- **Web Interface**: `docs/WEB_EXPLORER_INTEGRATION.md`
- **CLI Tools**: `scripts/README_EXPLORER.md`
- **Quick Reference**: `scripts/QUICK_REFERENCE.md`
- **Implementation**: `docs/DATABASE_EXPLORER.md`

## 🚀 Next Steps

1. **Explore your data**: Browse projects and collections
2. **Try a search**: Find a specific vector
3. **Check stats**: View usage and user statistics
4. **Automate**: Create scripts using CLI tools
5. **Report**: Generate weekly usage reports

**Pro Tip**: Start with the web interface for exploration, then use CLI for automation and scripting!

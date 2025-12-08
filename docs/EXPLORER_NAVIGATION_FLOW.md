# Database Explorer - Navigation Flow Guide

## 🎯 Three Ways to Browse Vector Data

### Method 1: Quick Browse from Projects List (Fastest)
```
Projects Tab
└── simple_test
    ├── 2 collections • 4 vectors
    └── Quick browse: [docs] [articles]  ← Click any collection button
                       ↓
    Automatically switches to Browse Rows tab
    Form pre-filled with project + collection
```

**Steps**:
1. Stay on Projects tab
2. See project row with "Quick browse: [docs] [articles]" buttons
3. Click a collection button (e.g., `docs`)
4. Automatically jumps to Browse Rows tab with form filled
5. Just select shard and click "Load Rows"

**Use Case**: Fastest way when you know which collection you want

---

### Method 2: Project Details → Collection → Browse (Most Visual)
```
Projects Tab
└── Click "simple_test" project
    ↓
    Modal opens showing collections
    └── Collection: docs
        ├── Dimension: 768, Metric: cosine
        ├── Shards: 4, Total Vectors: 4
        ├── [📋 Browse Rows] button  ← Click this
        └── Shard Distribution:
            [Shard 0: 2 vectors] ← Or click specific shard
            [Shard 1: 0 vectors]
            [Shard 2: 1 vector]  ← Click to auto-browse
            [Shard 3: 1 vector]
```

**Steps**:
1. Click project name to open details modal
2. See all collections with stats
3. **Option A**: Click "📋 Browse Rows" button on collection
   - Switches to Browse Rows tab
   - Pre-fills project + collection
   - Form highlighted for 2 seconds
4. **Option B**: Click a shard with vectors (green box)
   - Switches to Browse Rows tab
   - Pre-fills project + collection + shard
   - Auto-submits and loads rows immediately!

**Use Case**: Best when exploring data structure first

---

### Method 3: Manual Browse (Full Control)
```
Browse Rows Tab
└── Fill form manually:
    ├── Project ID: simple_test
    ├── Collection: docs
    ├── Shard ID: 0
    └── Limit: 50 rows
    ↓
    [📋 Load Rows] button
    ↓
    Table displays with:
    ├── ID column
    ├── Document preview
    ├── Metadata
    ├── Vector dimension
    ├── Created timestamp
    └── [View] button for details
```

**Steps**:
1. Click "Browse Rows" tab
2. Enter project ID, collection, shard ID
3. Choose limit (10, 25, 50, or 100)
4. Click "Load Rows"
5. Click "View" on any row for full details

**Use Case**: When you know exact shard or want specific limit

---

## 🎨 Visual Guide

### Projects List View
```
┌────────────────────────────────────────────────────────────┐
│ All Projects                                                │
│ Click a project to view its collections and shards         │
├────────────────────────────────────────────────────────────┤
│ simple_test                                    Quick browse:│
│ 2 collections • 4 vectors                     [docs] [art.]│→ Direct
│                                                             │
│ demo_project                              Quick browse:     │
│ 3 collections • 50 vectors      [blog] [wiki] [faqs]      │→ Direct
│                                                             │
│ semantic_search_demo                      Quick browse:     │
│ 1 collections • 10 vectors                        [data]   │→ Direct
└────────────────────────────────────────────────────────────┘
```

### Project Details Modal
```
┌────────────────────────────────────────────────────────────┐
│ Project: simple_test                                   [X] │
├────────────────────────────────────────────────────────────┤
│                                                             │
│ Collection: docs                      [📋 Browse Rows] ←─┐ │
│ ┌─────────────────────────────────────────────────────┐ │ │
│ │ Dimension: 768        Metric: cosine                │ │ │
│ │ Shards: 4             Total Vectors: 4              │ │ │
│ │                                                       │ │ │
│ │ Shard Distribution:                                  │ │ │
│ │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │ │ │
│ │ │Shard 0 │ │Shard 1 │ │Shard 2 │ │Shard 3 │        │ │ │
│ │ │   2    │ │   0    │ │   1    │ │   1    │        │ │ │
│ │ │ GREEN  │ │  GRAY  │ │ GREEN  │ │ GREEN  │        │ │ │
│ │ │Click to│ │disabled│ │Click to│ │Click to│        │ │ │
│ │ │ browse │ │        │ │ browse │ │ browse │        │ │ │
│ │ └────────┘ └────────┘ └────────┘ └────────┘        │ │ │
│ └─────────────────────────────────────────────────────┘ │ │
│                                                         │ │ │
│ Both navigate to Browse Rows tab ──────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### Browse Rows Tab (After Navigation)
```
┌────────────────────────────────────────────────────────────┐
│ Browse Vector Rows                                          │
│                                                             │
│ Form is PRE-FILLED and HIGHLIGHTED:                        │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Project ID: simple_test  ← Auto-filled                 │
│ │ Collection: docs         ← Auto-filled                 │
│ │ Shard ID: 0              ← Auto-filled (if clicked)    │
│ │ Limit: [50 rows ▼]                                     │
│ │ [📋 Load Rows]           ← Auto-clicked if shard      │
│ └─────────────────────────────────────────────────────┘   │
│                                                             │
│ Table appears with data...                                 │
└────────────────────────────────────────────────────────────┘
```

---

## 🚀 Navigation Features

### 1. Quick Browse Buttons
**Where**: Projects list (right side)
**Shows**: Up to 3 collection names as buttons
**Action**: Click → Browse Rows tab with pre-filled form
**Best for**: Quick access to known collections

### 2. Browse Rows Button
**Where**: Collection details in modal
**Shows**: Blue button with "📋 Browse Rows"
**Action**: Click → Browse Rows tab, form highlighted
**Best for**: After reviewing collection stats

### 3. Clickable Shards
**Where**: Shard distribution grid in modal
**Shows**: Green boxes with vector counts
**Action**: Click → Auto-load rows from that shard
**Best for**: Direct access to specific shard data

### 4. Visual Feedback
- **Form highlighting**: 2-second blue ring when navigated
- **Hover effects**: Shard boxes darken on hover
- **Disabled state**: Gray boxes for empty shards
- **Auto-submit**: Shard clicks load data automatically

---

## 💡 Usage Examples

### Example 1: Quick Data Check
**Goal**: See what's in simple_test/docs
```
1. Open Database Explorer
2. See "simple_test" in list
3. Click [docs] button in "Quick browse"
4. Select shard 0
5. Click "Load Rows"
✓ Done in 3 clicks!
```

### Example 2: Explore Unknown Project
**Goal**: Understand demo_project structure
```
1. Click "demo_project" to open modal
2. See 3 collections: blog, wiki, faqs
3. Click "📋 Browse Rows" on "blog" collection
4. Form opens with blog pre-filled
5. Try different shards to see distribution
✓ Visual exploration first, then browse
```

### Example 3: Find Specific Vector
**Goal**: Browse shard 2 of semantic_search_demo/data
```
1. Click "semantic_search_demo" in list
2. Modal shows data collection
3. See shard distribution: Shard 2 has 5 vectors
4. Click the "Shard 2" green box
5. Rows automatically load!
✓ Fastest path - direct shard access
```

### Example 4: Compare Shard Contents
**Goal**: See different shards in same collection
```
1. Click project → open modal
2. Click "Shard 0" green box → loads rows
3. Click "Browse Rows" tab
4. Change shard to 2
5. Click "Load Rows" → see different data
✓ Easy comparison
```

---

## 🎨 UI Elements

### Clickable Elements

**Green Shard Boxes**:
```
┌────────────┐
│  Shard 0   │  ← Hover: darker green
│     5      │     Cursor: pointer
│ Click to   │     Click: loads data
│  browse    │
└────────────┘
```

**Gray Shard Boxes** (disabled):
```
┌────────────┐
│  Shard 1   │  ← No hover effect
│     0      │     Cursor: not-allowed
│            │     Click: nothing
└────────────┘
```

**Collection Buttons**:
```
[docs]  ← White background
        Hover: gray background
        Border: gray
        Click: navigate to browse
```

**Browse Rows Button**:
```
[📋 Browse Rows]  ← Indigo background
                   White text
                   Hover: darker indigo
```

### Visual States

**Form Highlighting** (2 seconds after navigation):
```
┌─────────────────────────────────┐
│ ███ Blue ring around form  ███  │ ← Attention grabber
│ Project ID: simple_test         │
│ Collection: docs                │
└─────────────────────────────────┘
```

**Auto-submit Animation**:
```
Click shard → Switch tab → Fill form → Submit → Load rows
  (instant)    (instant)    (100ms)    (auto)    (API call)
```

---

## 🔧 Technical Details

### Event Handlers

**browseCollection(projectId, collection)**:
```javascript
1. Close modal
2. Switch to 'browse' tab
3. Fill form: project_id, collection
4. Set shard_id to 0 (default)
5. Scroll to form
6. Add highlight ring for 2 seconds
```

**browseShardDirect(projectId, collection, shardId)**:
```javascript
1. Close modal
2. Switch to 'browse' tab
3. Fill form: project_id, collection, shard_id
4. Wait 100ms
5. Auto-submit form
6. Load rows immediately
```

### Form Pre-filling
```javascript
form.elements['project_id'].value = projectId;
form.elements['collection'].value = collection;
form.elements['shard_id'].value = shardId;
```

### Event Propagation
```html
<button onclick="event.stopPropagation(); browseCollection(...)">
<!-- Prevents parent click handler from triggering -->
```

---

## 📊 Navigation Comparison

| Method | Clicks | Speed | Best For |
|--------|--------|-------|----------|
| Quick Browse Button | 2-3 | ⚡⚡⚡ Fast | Known collections |
| Project → Collection → Browse | 3-4 | ⚡⚡ Medium | Exploring structure |
| Project → Shard Click | 2 | ⚡⚡⚡ Fastest | Specific shard access |
| Manual Form Fill | 4-5 | ⚡ Slower | Custom parameters |

---

## 🎯 Best Practices

1. **First-time exploration**: Use Project → Collection flow to understand data structure
2. **Routine browsing**: Use Quick Browse buttons for instant access
3. **Shard-specific**: Click shard boxes for immediate data load
4. **Large datasets**: Use manual form to control limit parameter
5. **Multiple collections**: Keep modal open and click different "Browse Rows" buttons

---

## 🚦 Navigation Flow Chart

```
Start: Database Explorer Page
│
├─ Goal: Quick peek at known collection
│  └─→ Click collection button in projects list
│     └─→ Browse Rows tab opens (pre-filled)
│        └─→ Select shard → Load Rows
│
├─ Goal: Explore project structure
│  └─→ Click project name
│     └─→ Modal shows collections + shards
│        ├─→ Click "Browse Rows" button
│        │   └─→ Browse Rows tab (highlighted)
│        │
│        └─→ Click specific shard box
│            └─→ Rows auto-load immediately!
│
└─ Goal: Custom browsing
   └─→ Click "Browse Rows" tab
      └─→ Fill form manually
         └─→ Load Rows
```

This navigation system makes exploring your vector database intuitive and fast! 🚀

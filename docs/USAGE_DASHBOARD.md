# Usage Dashboard Documentation

## Overview

The Usage Dashboard provides comprehensive visualization and monitoring of Phase 4 metrics including:
- Operations statistics and performance metrics
- Vector processing analytics
- User and project activity tracking
- Quota consumption monitoring
- Real-time operation logging

## Features

### 1. Summary Cards 📊

Four key metric cards displaying:

- **Total Operations**: Count of all API operations (add, search, update, delete)
- **Vectors Processed**: Total number of vectors handled across all operations
- **Data Volume**: Total payload size processed (formatted in KB/MB/GB)
- **Success Rate**: Percentage of successful operations vs total attempts

### 2. Operations Breakdown Chart 📈

Interactive Chart.js bar chart showing:
- Operations count by type (add, search, update, delete, batch operations)
- Vectors processed per operation type
- Visual comparison of operation distribution
- Hover tooltips with detailed statistics

### 3. Top Users Table 👥

Displays most active users with:
- Username
- Total operations performed
- Vectors processed
- Sorted by activity level (most active first)
- Shows top 10 users

### 4. Top Projects Table 📁

Shows most active projects including:
- Project ID
- Total operations count
- Vectors processed in project
- Sorted by activity level
- Shows top 10 projects

### 5. Quota Status Monitoring ⚡

Real-time quota consumption with:
- User-level quotas with current usage
- Project-level quotas with current usage
- Color-coded progress bars:
  - 🟢 **Green**: < 75% usage (healthy)
  - 🟡 **Yellow**: 75-90% usage (warning)
  - 🔴 **Red**: > 90% usage (critical)
- Percentage and absolute usage values

### 6. Recent Operations Table 🕐

Detailed log of recent activity showing:
- Timestamp (formatted: "Jan 15, 2025 14:30:45")
- Username who performed the operation
- Project ID
- Operation type (add_vector, batch_add_vector, search, etc.)
- Number of vectors processed
- Payload size
- Status (success/failure)
- Duration in milliseconds
- Shows last 50 operations

### 7. Time Range Filter 📅

Dropdown selector to filter data by:
- **Last 24 Hours**: Today's activity
- **Last 7 Days**: This week's metrics
- **Last 30 Days**: This month's statistics
- **All Time**: Complete historical data

Page auto-refreshes when time range changes.

## Technical Implementation

### Backend Route

**File**: `app/adapters/rest/admin_routes.py`

**Endpoint**: `GET /admin/usage`

**Query Parameters**:
- `time_range` (optional): "24h", "7d", "30d", or "all" (default: "all")

**Response**: HTML template with context data

**Key Functions**:
```python
@router.get("/usage")
async def usage_dashboard(
    request: Request,
    time_range: str = "all",
    current_user: dict = Depends(require_admin_cookie)
):
    # Calculate time window
    since_timestamp = calculate_time_window(time_range)
    
    # Get usage statistics
    stats = usage_storage.get_usage_stats(since=since_timestamp)
    
    # Aggregate user statistics
    user_stats = aggregate_user_stats(stats['records'])
    
    # Aggregate project statistics
    project_stats = aggregate_project_stats(stats['records'])
    
    # Get quota status
    quotas = quota_storage.get_all_quotas()
    
    # Prepare chart data
    chart_data = prepare_chart_data(stats['by_operation'])
    
    # Get recent operations (with username joins)
    recent_ops = get_recent_operations(stats['records'], limit=50)
    
    return templates.TemplateResponse("admin/usage.html", {
        "request": request,
        "stats": stats,
        "user_stats": user_stats,
        "project_stats": project_stats,
        "quotas": quotas,
        "chart_data": chart_data,
        "recent_ops": recent_ops,
        "time_range": time_range
    })
```

### Frontend Template

**File**: `templates/admin/usage.html`

**Technologies**:
- **Tailwind CSS**: Responsive styling and layout
- **Chart.js**: Interactive data visualizations
- **Jinja2**: Template rendering with Python integration

**Key Sections**:

1. **Summary Cards** (lines 10-50):
   ```html
   <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
       <!-- Operations Card -->
       <div class="bg-white rounded-lg shadow p-6">
           <div class="text-gray-500 text-sm">Total Operations</div>
           <div class="text-3xl font-bold">{{ stats.total_operations|format_number }}</div>
       </div>
       <!-- More cards... -->
   </div>
   ```

2. **Chart.js Configuration** (lines 262-310):
   ```javascript
   const ctx = document.getElementById('operationsChart').getContext('2d');
   new Chart(ctx, {
       type: 'bar',
       data: {
           labels: {{ chart_data.labels|tojson }},
           datasets: [{
               label: 'Operations',
               data: {{ chart_data.operations|tojson }},
               backgroundColor: 'rgba(59, 130, 246, 0.5)'
           }]
       }
   });
   ```

3. **Time Range Selector** (lines 312-330):
   ```javascript
   function changeTimeRange() {
       const range = document.getElementById('timeRange').value;
       window.location.href = `/admin/usage?time_range=${range}`;
   }
   ```

### Number Formatting Filter

**File**: `app/adapters/rest/admin_routes.py` (lines 23-27)

```python
def format_number(value):
    """Format number with thousands separator."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

templates.env.filters["format_number"] = format_number
```

**Usage in Template**:
```jinja2
{{ stats.total_operations|format_number }}
<!-- Outputs: 1,234 instead of 1234 -->
```

## Data Model

### Usage Statistics Structure

```python
{
    'total_operations': int,          # Total count of all operations
    'total_vectors': int,             # Total vectors processed
    'total_payload_size': int,        # Total bytes processed
    'by_operation': {                 # Breakdown by operation type
        'operation_type': {
            'count': int,             # Number of operations
            'vectors': int,           # Vectors processed
            'avg_duration_ms': float  # Average duration
        }
    },
    'records': [                      # Raw operation records
        {
            'id': int,
            'user_id': str,
            'project_id': str,
            'operation_type': str,
            'vectors_count': int,
            'payload_size': int,
            'duration_ms': float,
            'status': str,
            'timestamp': datetime
        }
    ]
}
```

### Quota Status Structure

```python
{
    'user_quotas': [
        {
            'user_id': str,
            'current_usage': int,
            'quota_limit': int,
            'usage_percentage': float
        }
    ],
    'project_quotas': [
        {
            'project_id': str,
            'current_usage': int,
            'quota_limit': int,
            'usage_percentage': float
        }
    ]
}
```

## Access Instructions

### Via Web Browser

1. **Navigate to Admin Panel**:
   ```
   http://localhost:8000/admin
   ```

2. **Login with Admin Credentials**:
   - Username: `admin`
   - Password: Your admin password

3. **Click "Usage" in Navigation Menu**:
   - Located between "Dashboard" and "Users"

4. **View Dashboard**:
   - Summary metrics load automatically
   - Chart displays operations breakdown
   - Tables show top users/projects
   - Quota status indicators update in real-time

### Via API (for programmatic access)

```python
import requests

# Authenticate
session = requests.Session()
resp = session.post(
    "http://localhost:8000/admin/login",
    data={"username": "admin", "password": "your_password"}
)

# Access dashboard data
resp = session.get(
    "http://localhost:8000/admin/usage",
    params={"time_range": "7d"}
)
html = resp.text
```

## Demo Script

**File**: `demo_usage_dashboard.py`

### Purpose
Generates sample usage data to populate the dashboard for demonstration and testing.

### Usage
```bash
python3 demo_usage_dashboard.py
```

### What It Does
1. Creates demo project and collection
2. Adds 10 individual vectors
3. Batch adds 50 vectors
4. Performs 10 searches
5. Batch updates 5 vectors
6. Batch deletes 10 vectors
7. Displays current statistics
8. Shows dashboard access instructions

### Sample Output
```
📊 Current Statistics:
   Total Operations: 31
   Total Vectors: 445
   Total Payload: 2.71 MB

   By Operation Type:
      batch_update_vector: 4 operations, 155 vectors
      batch_delete_vector: 4 operations, 70 vectors
      batch_add_vector: 3 operations, 200 vectors
      add_vector: 10 operations, 10 vectors
      search: 10 operations, 10 vectors
```

## Performance Metrics

### Page Load Time
- **Initial Load**: < 500ms (with cached data)
- **Time Range Change**: < 300ms (simple page refresh)

### Data Volume Handling
- **Recent Operations**: Limited to 50 most recent (fast queries)
- **Chart Data**: Aggregated by operation type (6-8 data points)
- **Top Lists**: Limited to 10 users/projects (efficient rendering)

### Database Queries
1. `get_usage_stats(since=...)`: Single query with time filter
2. `get_all_quotas()`: Cached quota data
3. User joins: In-memory aggregation (no additional queries)

## Security Considerations

### Authentication
- **Required**: Admin-level authentication via cookie
- **Middleware**: `require_admin_cookie` dependency
- **Session**: Secure session management

### Authorization
- **Admin Only**: Only admin users can access dashboard
- **No Public Access**: Returns 401/403 for unauthorized requests

### Data Protection
- **No PII Exposure**: Only displays usernames (no passwords/emails)
- **Aggregated Data**: Individual operations shown but no sensitive metadata
- **Rate Limiting**: Standard API rate limits apply

## Troubleshooting

### Dashboard Not Loading

**Issue**: 401 Authentication Required
**Solution**: Login via `/admin` first, ensure session cookie is set

**Issue**: 500 Internal Server Error
**Solution**: Check server logs for database connection issues

### No Data Showing

**Issue**: All metrics show zero
**Solution**: Run `demo_usage_dashboard.py` to generate sample data

**Issue**: Old data showing
**Solution**: Change time range filter or refresh page

### Chart Not Rendering

**Issue**: Chart.js errors in console
**Solution**: Verify Chart.js CDN is accessible, check browser console

### Slow Load Times

**Issue**: Page takes > 2 seconds to load
**Solution**: 
- Check database size (consider archiving old records)
- Verify indexes exist on timestamp columns
- Reduce time range to smaller window

## Future Enhancements

### Planned Features

1. **Export Functionality** 📥
   - CSV export of usage records
   - JSON export for analysis
   - Date range selection for exports

2. **Real-time Updates** 🔄
   - WebSocket integration for live updates
   - Auto-refresh without page reload
   - Live operation notifications

3. **Advanced Filtering** 🔍
   - Filter by user
   - Filter by project
   - Filter by operation type
   - Custom date ranges

4. **Additional Charts** 📊
   - Line chart for trends over time
   - Pie chart for operation distribution
   - Stacked bar chart for user/project breakdown

5. **Alerts & Notifications** 🔔
   - Quota threshold alerts
   - Unusual activity detection
   - Performance degradation warnings

## Related Documentation

- [Phase 4 Summary](PHASE4_USAGE_AND_ADVANCED_FEATURES.md)
- [Batch Operations](BATCH_OPERATIONS.md)
- [Authentication System](AUTH_FIX_SUMMARY.md)
- [Admin UI](PHASE2_ADMIN_UI.md)

## Support

For issues or questions:
1. Check server logs: `tail -f logs/app.log`
2. Run demo script: `python3 demo_usage_dashboard.py`
3. Verify authentication: Check admin cookie is set
4. Review this documentation for troubleshooting steps

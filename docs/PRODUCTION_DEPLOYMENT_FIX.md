# 🚀 Production Deployment Fix Guide

## Issue Summary

The Database Explorer web interface is failing on production with:
```
ModuleNotFoundError: No module named 'pandas'
```

This happens because the web interface imports `scripts.db_explorer` which requires `pandas`, `lancedb`, and `pyarrow` packages that weren't installed in your production environment.

---

## ✅ Solutions Applied (Code Changes)

### 1. Made pandas import optional in `scripts/db_explorer.py`
- Changed from hard exit on import failure to graceful degradation
- Only exits if running as CLI (not when imported by web interface)
- Returns list of dicts instead of DataFrame when pandas unavailable

### 2. Updated `app/adapters/rest/admin_routes.py`
- Handles both DataFrame and list formats
- Works whether pandas is installed or not

### 3. Added pandas to `requirements.txt`
- Ensures it's installed in future deployments

---

## 🔧 What You Need To Do on Production

### Option A: Quick Fix - Install Just Pandas (30 seconds)

If you want to fix immediately without pulling new code:

```bash
# Navigate to your production directory
cd /var/www/fastuser/data/www/vector.veronikalove.com/v2

# Activate virtual environment
source .venv/bin/activate

# Install missing package
pip install pandas

# Restart the service (use your actual restart command)
systemctl restart embeddings-service
# OR
pkill -f "python.*main.py" && python3 main.py &
```

### Option B: Full Update with Makefile (Recommended - 2 minutes)

This ensures all dependencies are properly installed:

```bash
# Navigate to your production directory
cd /var/www/fastuser/data/www/vector.veronikalove.com/v2

# Pull latest code (includes pandas in requirements.txt)
git pull

# Run complete setup (installs deps + generates proto)
make setup

# Restart service
systemctl restart embeddings-service
# OR
pkill -f "python.*main.py" && python3 main.py &
```

**What `make setup` does:**
- Creates/updates virtual environment
- Upgrades pip to latest version
- Installs all packages from `requirements.txt` including:
  - pandas (for data manipulation)
  - lancedb (for vector database)
  - pyarrow (for columnar data)
  - All other dependencies
- Generates gRPC protocol buffer files automatically
- Provides helpful next-steps output

**Alternative: Just update dependencies**
```bash
# If you just want to update packages without full setup
make deps  # Also generates proto files automatically
```

### Option C: Manual Install All Required Packages

### Option C: Manual Install All Required Packages

If you can't use `make deps`:

```bash
# Navigate to your production directory
cd /var/www/fastuser/data/www/vector.veronikalove.com/v2

# Activate virtual environment
source .venv/bin/activate

# Install missing packages manually
pip install pandas lancedb pyarrow

# Or install all requirements
pip install -r requirements.txt

# Restart the service
systemctl restart embeddings-service
```

---

## ✅ Verification Steps

After installation, verify everything works:

### 1. Check packages are installed (New!)
```bash
# Using the built-in dependency checker
make check-deps

# OR manually
python3 scripts/check_dependencies.py

# OR check specific packages
python3 -c "import pandas, lancedb, pyarrow; print('✅ All packages installed')"
```

### 2. Test the database explorer endpoint
```bash
curl -s "http://localhost:8000/admin/explorer" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  | grep -o "Database Explorer" && echo "✅ Explorer loads"
```

### 3. Check service logs
```bash
# Look for any import errors
tail -f /path/to/your/service.log
```

---

## 🎯 Alternative: Disable Database Explorer (Emergency Fix)

If you can't install packages immediately, you can temporarily disable the explorer:

```bash
# Comment out the explorer routes in main.py or admin_routes.py
# This will make the explorer unavailable but won't crash the service
```

**Edit `app/adapters/rest/admin_routes.py`:**
```python
# Temporarily comment out these routes:
# @router.get("/explorer")
# @router.get("/explorer/project/{project_id}")
# @router.get("/explorer/search")
# @router.get("/explorer/rows")
```

Then restart the service.

---

## 📊 Package Size Information

These are the packages being added:
- **pandas**: ~40 MB (data manipulation library)
- **lancedb**: ~5 MB (vector database client)
- **pyarrow**: ~80 MB (columnar data format)

**Total additional space**: ~125 MB

Make sure you have sufficient disk space before installing.

---

## 🔍 Understanding the Fix

### What Changed:

**Before:**
```python
try:
    import pandas as pd
except ImportError:
    sys.exit(1)  # ❌ Kills entire process
```

**After:**
```python
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False  # ✅ Graceful degradation

# Only exit if running as CLI
if __name__ == "__main__" and not HAS_PANDAS:
    sys.exit(1)
```

**Result:**
- CLI tool still requires pandas (for pretty formatting)
- Web interface works without pandas (returns plain dicts)
- Best of both worlds: install pandas for full features, works without for basic functionality

---

## ⚠️ Important Notes

1. **Virtual Environment**: Make sure you activate the correct virtual environment before installing packages
   ```bash
   source .venv/bin/activate
   which pip  # Should show path inside .venv
   ```

2. **Python Version**: pandas requires Python 3.8+. Check your version:
   ```bash
   python3 --version
   ```

3. **Permissions**: If you get permission errors, you might need sudo or need to be the correct user:
   ```bash
   sudo -u fastuser pip install pandas lancedb pyarrow
   ```

4. **Service Restart**: Don't forget to restart the service after installing packages!

---

## 🆘 Troubleshooting

### Issue: "pip: command not found"
```bash
# Install pip first
python3 -m ensurepip --upgrade
```

### Issue: "Permission denied"
```bash
# Use correct user
sudo -u fastuser bash
source .venv/bin/activate
pip install pandas lancedb pyarrow
```

### Issue: "No space left on device"
```bash
# Check available space
df -h

# Clean up if needed
pip cache purge
apt autoremove  # (if you have sudo)
```

### Issue: Installation takes too long
```bash
# Use binary wheels instead of building from source
pip install --only-binary :all: pandas lancedb pyarrow
```

---

## 🎉 Success Indicators

After successful deployment, you should be able to:

1. ✅ Access `http://vector.veronikalove.com/admin/explorer` without errors
2. ✅ See the 4-tab interface (Projects, Browse Rows, Search, Auth)
3. ✅ Click on collections and see data
4. ✅ Browse vector rows in table format
5. ✅ Search for vectors by ID

---

## 📞 Need Help?

If issues persist after following this guide:

1. **Check Python version**: `python3 --version` (need 3.8+)
2. **Check virtual environment**: `which python3` (should be in .venv)
3. **Check error logs**: Look for specific error messages
4. **Verify packages**: `pip list | grep -E 'pandas|lancedb|pyarrow'`

Common command to gather diagnostics:
```bash
echo "Python: $(python3 --version)"
echo "Pip: $(pip --version)"
echo "Virtual env: $(which python3)"
pip list | grep -E 'pandas|lancedb|pyarrow|fastapi'
```

Send this output if you need further assistance.

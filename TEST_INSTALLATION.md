# 🧪 Test Installation Guide

This guide helps you test the complete installation from scratch (fresh git clone).

## Test Scenario: Clean Installation

```bash
# 1. Navigate to a temporary directory
cd /tmp

# 2. Clone the repository (simulating fresh install)
git clone https://github.com/vitosgeen/embeddings-generator.git test-embeddings
cd test-embeddings

# 3. Check help (should work without any setup)
make help

# 4. Run complete setup
make setup

# 5. Verify dependencies
make check-deps

# 6. Configure API key
echo "API_KEYS=admin:sk-test-123456789" > .env

# 7. Start the service
make run &

# Wait for service to start
sleep 5

# 8. Test health endpoint
curl http://localhost:8000/health

# 9. Test embedding endpoint
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-test-123456789" \
  -d '{"text": "Test embedding"}'

# 10. Test admin login (if needed)
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# 11. Stop the service
make stop

# 12. Cleanup
cd /tmp
rm -rf test-embeddings
```

## ✅ Expected Results

### After `make help`:
```
🚀 Embeddings Service - Available Commands
==========================================
[... help output ...]
```

### After `make setup`:
```
📚 Installing dependencies...
✅ Dependencies installed.
⚙️  Generating gRPC stubs...
✅ Setup complete! Run 'make run' to start the service.
🎉 All done! Your environment is ready.
```

### After `make check-deps`:
```
Required packages: 9/9 installed
🎉 All required dependencies are installed!
```

### After health check:
```json
{
  "status": "healthy",
  "model": "intfloat/multilingual-e5-base",
  "device": "cpu",
  "dimension": 768
}
```

### After embed test:
```json
{
  "dim": 768,
  "embedding": [0.123, -0.456, ...],
  "task_type": "passage"
}
```

## 🐛 Troubleshooting During Test

### Issue: `make: command not found`
```bash
# Install make (Ubuntu/Debian)
sudo apt-get install make

# Install make (macOS)
brew install make
```

### Issue: `python3: command not found`
```bash
# Install Python 3 (Ubuntu/Debian)
sudo apt-get install python3 python3-venv python3-pip

# Install Python 3 (macOS)
brew install python3
```

### Issue: Port 8000 already in use
```bash
# Check what's using the port
lsof -i :8000

# Kill the process
make stop

# Or manually
kill -9 $(lsof -ti:8000)
```

### Issue: Service won't start
```bash
# Check logs
tail -f /tmp/embeddings.log

# Verify Python version (need 3.8+)
python3 --version

# Verify virtual environment
ls -la .venv/
```

## 📊 Test Checklist

Use this checklist when testing:

- [ ] `git clone` works
- [ ] `make help` shows all commands
- [ ] `make setup` completes without errors
- [ ] Virtual environment created in `.venv/`
- [ ] Proto files generated in `proto/`
- [ ] `make check-deps` shows all packages installed
- [ ] Service starts with `make run`
- [ ] Health endpoint responds
- [ ] Embed endpoint works with auth
- [ ] `make stop` stops all services
- [ ] No processes left on port 8000/50051

## 🎯 Quick One-Liner Test

```bash
cd /tmp && \
git clone https://github.com/vitosgeen/embeddings-generator.git test-install && \
cd test-install && \
make setup && \
echo "API_KEYS=test:sk-test-key" > .env && \
make run & sleep 5 && \
curl http://localhost:8000/health && \
make stop && \
cd .. && rm -rf test-install && \
echo "✅ Installation test complete!"
```

## 📝 Notes for Production Testing

When testing on your production server:

1. **Use a test directory first**:
   ```bash
   cd /var/www/fastuser/data/www/vector.veronikalove.com/
   mkdir test-install
   cd test-install
   git clone [your-repo] .
   make setup
   ```

2. **Verify before deploying**:
   - Check all dependencies install correctly
   - Test with your actual API keys
   - Verify DB Explorer works: `/admin/explorer`
   - Run tests: `make test`

3. **Then deploy to actual location**:
   ```bash
   cd /var/www/fastuser/data/www/vector.veronikalove.com/v2
   git pull
   make setup
   systemctl restart embeddings-service
   ```

## 🔍 What to Report

If you encounter issues, please report:

1. **Environment**:
   - OS: `uname -a`
   - Python version: `python3 --version`
   - Make version: `make --version`

2. **Error output**:
   - Full console output of failed command
   - Any error messages from logs

3. **State**:
   - Which step failed
   - What files were created (if any)
   - Output of `ls -la`

Good luck with your testing! 🚀

#!/bin/bash
# Demo script for Database Explorer

echo "======================================================================"
echo "  🔍 Database Explorer Demo"
echo "======================================================================"
echo ""
echo "This script demonstrates the Database Explorer tool's capabilities."
echo ""

# Check if service is running
if ! pgrep -f "python3 main.py" > /dev/null; then
    echo "⚠️  Service not running. Starting it..."
    python3 main.py > /tmp/embeddings-service.log 2>&1 &
    sleep 5
fi

echo "📊 Part 1: Vector Database Exploration"
echo "----------------------------------------------------------------------"
echo ""

echo "1️⃣ Listing all projects..."
python3 scripts/db_explorer.py << 'EOF' | tail -n 20
1
0
EOF

echo ""
echo "2️⃣ Checking simple_test project details..."
python3 scripts/db_explorer.py << 'EOF' | grep -A 20 "Collection Config\|Shard Information"
3
simple_test
docs
0
EOF

echo ""
echo ""
echo "👥 Part 2: Auth Database Exploration"
echo "----------------------------------------------------------------------"
echo ""

echo "3️⃣ User summary by role..."
python3 scripts/db_explorer.py << 'EOF' | grep -A 10 "User Summary"
9
0
EOF

echo ""
echo "4️⃣ API keys overview..."
python3 scripts/db_explorer.py << 'EOF' | grep -A 15 "API Keys"
7
5
0
EOF

echo ""
echo ""
echo "🔎 Part 3: Vector Search"
echo "----------------------------------------------------------------------"
echo ""

echo "5️⃣ Finding vector by ID (doc1)..."
python3 scripts/db_explorer.py << 'EOF' | grep -A 10 "Found in shard\|Vector not found"
5
simple_test
docs
doc1
0
EOF

echo ""
echo ""
echo "======================================================================"
echo "  ✅ Demo Complete!"
echo "======================================================================"
echo ""
echo "To explore interactively, run:"
echo "  python3 scripts/db_explorer.py"
echo ""
echo "For more details, see: scripts/README_EXPLORER.md"
echo ""

#!/usr/bin/env python3
"""Check if all required dependencies are installed for the Embeddings Service."""

import sys
from importlib import import_module

# Core dependencies
CORE_DEPS = {
    'fastapi': 'FastAPI web framework',
    'uvicorn': 'ASGI server',
    'sentence_transformers': 'Sentence Transformers for embeddings',
    'torch': 'PyTorch ML framework',
}

# Vector Database dependencies
VDB_DEPS = {
    'lancedb': 'LanceDB vector database',
    'pyarrow': 'Apache Arrow (required by LanceDB)',
}

# Database Explorer dependencies
EXPLORER_DEPS = {
    'pandas': 'Pandas data manipulation (for DB Explorer)',
}

# Authentication dependencies
AUTH_DEPS = {
    'sqlalchemy': 'SQLAlchemy ORM',
    'argon2': 'Argon2 password hashing',
}

# Testing dependencies
TEST_DEPS = {
    'pytest': 'pytest testing framework',
    'httpx': 'HTTPX async HTTP client',
}

def check_package(package_name: str) -> bool:
    """Check if a package is installed."""
    try:
        import_module(package_name)
        return True
    except ImportError:
        return False

def print_section(title: str, deps: dict, required: bool = True) -> tuple:
    """Print a section of dependencies and return counts."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    
    installed = 0
    missing = 0
    missing_list = []
    
    for pkg, desc in deps.items():
        status = check_package(pkg)
        if status:
            installed += 1
            print(f"✅ {pkg:25} - {desc}")
        else:
            missing += 1
            missing_list.append(pkg)
            symbol = "❌" if required else "⚠️ "
            print(f"{symbol} {pkg:25} - {desc}")
    
    return installed, missing, missing_list

def main():
    """Main function to check all dependencies."""
    print("\n" + "="*60)
    print("  🔍 Embeddings Service - Dependency Check")
    print("="*60)
    
    all_missing = []
    
    # Check core dependencies (required)
    core_ok, core_miss, core_list = print_section("Core Dependencies (Required)", CORE_DEPS, required=True)
    all_missing.extend(core_list)
    
    # Check VDB dependencies (required)
    vdb_ok, vdb_miss, vdb_list = print_section("Vector Database Dependencies (Required)", VDB_DEPS, required=True)
    all_missing.extend(vdb_list)
    
    # Check Explorer dependencies (required for web explorer)
    exp_ok, exp_miss, exp_list = print_section("Database Explorer Dependencies (Required for Web UI)", EXPLORER_DEPS, required=True)
    all_missing.extend(exp_list)
    
    # Check Auth dependencies (required)
    auth_ok, auth_miss, auth_list = print_section("Authentication Dependencies (Required)", AUTH_DEPS, required=True)
    all_missing.extend(auth_list)
    
    # Check Test dependencies (optional)
    test_ok, test_miss, test_list = print_section("Testing Dependencies (Optional)", TEST_DEPS, required=False)
    
    # Summary
    print(f"\n{'='*60}")
    print("  📊 Summary")
    print(f"{'='*60}")
    
    total_required = len(CORE_DEPS) + len(VDB_DEPS) + len(EXPLORER_DEPS) + len(AUTH_DEPS)
    total_installed = core_ok + vdb_ok + exp_ok + auth_ok
    total_missing = core_miss + vdb_miss + exp_miss + auth_miss
    
    print(f"Required packages: {total_installed}/{total_required} installed")
    print(f"Optional packages: {test_ok}/{len(TEST_DEPS)} installed")
    
    if all_missing:
        print(f"\n⚠️  Missing required packages: {', '.join(all_missing)}")
        print(f"\n💡 To install missing packages:")
        print(f"   make deps")
        print(f"   # OR")
        print(f"   pip install {' '.join(all_missing)}")
        return 1
    else:
        print(f"\n🎉 All required dependencies are installed!")
        if test_miss > 0:
            print(f"ℹ️  Some optional testing packages are missing (not critical)")
        return 0

if __name__ == "__main__":
    sys.exit(main())

import os
from typing import Dict, Set

MODEL_ID = os.getenv("MODEL_ID", "BAAI/bge-base-en-v1.5")
DEVICE = os.getenv("DEVICE", "auto")  # "auto"|"cpu"|"cuda"|"mps"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
REST_PORT = int(os.getenv("REST_PORT", "8000"))
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))

# Authentication
def _parse_api_keys() -> Dict[str, str]:
    """Parse API keys from environment variable.
    
    Format: account_name:api_key,account_name2:api_key2
    Returns: Dict mapping api_key -> account_name
    """
    api_keys_env = os.getenv("API_KEYS", "")
    if not api_keys_env:
        return {}
    
    api_keys = {}
    for pair in api_keys_env.split(","):
        if ":" in pair:
            account, key = pair.strip().split(":", 1)
            api_keys[key] = account
    
    return api_keys

API_KEYS: Dict[str, str] = _parse_api_keys()
VALID_API_KEYS: Set[str] = set(API_KEYS.keys())

import os
from typing import Dict, Set

# Default configuration values
DEFAULT_MODEL_ID = "BAAI/bge-base-en-v1.5"
DEFAULT_DEVICE = "auto"
DEFAULT_BATCH_SIZE = "32"
DEFAULT_REST_PORT = "8000" 
DEFAULT_GRPC_PORT = "50051"
DEFAULT_VDB_STORAGE_PATH = "./vdb-data"

# Environment variable names
ENV_MODEL_ID = "MODEL_ID"
ENV_DEVICE = "DEVICE"
ENV_BATCH_SIZE = "BATCH_SIZE"
ENV_REST_PORT = "REST_PORT"
ENV_GRPC_PORT = "GRPC_PORT"
ENV_API_KEYS = "API_KEYS"
ENV_VDB_STORAGE_PATH = "VDB_STORAGE_PATH"

# Device options (for documentation/validation)
DEVICE_AUTO = "auto"
DEVICE_CPU = "cpu"
DEVICE_CUDA = "cuda"
DEVICE_MPS = "mps"

# Configuration separator
API_KEYS_SEPARATOR = ","
API_KEY_PAIR_SEPARATOR = ":"

MODEL_ID = os.getenv(ENV_MODEL_ID, DEFAULT_MODEL_ID)
DEVICE = os.getenv(ENV_DEVICE, DEFAULT_DEVICE)  # "auto"|"cpu"|"cuda"|"mps"
BATCH_SIZE = int(os.getenv(ENV_BATCH_SIZE, DEFAULT_BATCH_SIZE))
REST_PORT = int(os.getenv(ENV_REST_PORT, DEFAULT_REST_PORT))
GRPC_PORT = int(os.getenv(ENV_GRPC_PORT, DEFAULT_GRPC_PORT))
VDB_STORAGE_PATH = os.getenv(ENV_VDB_STORAGE_PATH, DEFAULT_VDB_STORAGE_PATH)

# Authentication
def _parse_api_keys() -> Dict[str, str]:
    """Parse API keys from environment variable.
    
    Format: account_name:api_key,account_name2:api_key2
    Returns: Dict mapping api_key -> account_name
    """
    api_keys_env = os.getenv(ENV_API_KEYS, "")
    if not api_keys_env:
        return {}
    
    api_keys = {}
    for pair in api_keys_env.split(API_KEYS_SEPARATOR):
        if API_KEY_PAIR_SEPARATOR in pair:
            account, key = pair.strip().split(API_KEY_PAIR_SEPARATOR, 1)
            api_keys[key] = account
    
    return api_keys

API_KEYS: Dict[str, str] = _parse_api_keys()
VALID_API_KEYS: Set[str] = set(API_KEYS.keys())

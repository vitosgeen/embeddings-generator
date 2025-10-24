import os

MODEL_ID = os.getenv("MODEL_ID", "BAAI/bge-base-en-v1.5")
DEVICE = os.getenv("DEVICE", "auto")  # "auto"|"cpu"|"cuda"|"mps"
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
REST_PORT = int(os.getenv("REST_PORT", "8000"))
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))

import asyncio
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.bootstrap import build_usecase, build_vdb_usecases
from app.adapters.rest.fastapi_app import build_fastapi
from app.adapters.grpc.server import serve_grpc
from app.config import REST_PORT, GRPC_PORT

# Server configuration constants
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOG_LEVEL = "info"

async def run():
    # Build embedding service use case
    uc = build_usecase()
    
    # Build VDB use cases
    vdb_usecases = build_vdb_usecases()
    
    # Build FastAPI app with both embedding and VDB services
    app = build_fastapi(uc, vdb_usecases)

    # gRPC server (asynchronous)
    grpc_server = await serve_grpc(uc, port=GRPC_PORT)

    # FastAPI (uvicorn) also asynchronous
    config = uvicorn.Config(app, host=DEFAULT_HOST, port=REST_PORT, log_level=DEFAULT_LOG_LEVEL)
    server = uvicorn.Server(config)

    # run in parallel
    await asyncio.gather(server.serve(), grpc_server.wait_for_termination())

if __name__ == "__main__":
    asyncio.run(run())

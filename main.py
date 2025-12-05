import asyncio
import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.bootstrap import build_usecase, build_vdb_usecases
from app.bootstrap_auth import bootstrap_auth_database
from app.adapters.rest.fastapi_app import build_fastapi
from app.adapters.grpc.server import serve_grpc
from app.adapters.infra.task_queue import get_task_queue
from app.adapters.infra.task_handlers import register_default_handlers
from app.config import REST_PORT, GRPC_PORT

# Server configuration constants
DEFAULT_HOST = "0.0.0.0"
DEFAULT_LOG_LEVEL = "info"

logger = logging.getLogger(__name__)

async def run():
    # Bootstrap authentication database (idempotent)
    logger.info("Bootstrapping authentication database...")
    bootstrap_auth_database()
    
    # Initialize task queue and register handlers
    logger.info("Initializing task queue...")
    task_queue = get_task_queue()
    register_default_handlers()
    task_queue.start_worker()
    logger.info("Task queue worker started")
    
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

import asyncio
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.bootstrap import build_usecase
from app.adapters.rest.fastapi_app import build_fastapi
from app.adapters.grpc.server import serve_grpc
from app.config import REST_PORT, GRPC_PORT

async def run():
    uc = build_usecase()
    app = build_fastapi(uc)

    # gRPC сервер (асинхронний)
    grpc_server = await serve_grpc(uc, port=GRPC_PORT)

    # FastAPI (uvicorn) теж асинхронно
    config = uvicorn.Config(app, host="0.0.0.0", port=REST_PORT, log_level="info")
    server = uvicorn.Server(config)

    # працюємо паралельно
    await asyncio.gather(server.serve(), grpc_server.wait_for_termination())

if __name__ == "__main__":
    asyncio.run(run())

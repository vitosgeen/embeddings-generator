from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from ...usecases.generate_embedding import GenerateEmbeddingUC
from ...domain.auth import AuthContext
from .auth_middleware import get_current_user, AuthenticationMiddleware
from .vdb_routes import build_vdb_router
from .admin_routes import build_admin_router
from .task_routes import router as task_router
from ...utils.text_chunking import (
    chunk_text,
    combine_embeddings,
    should_chunk,
    get_chunking_info,
)


class EmbedReq(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None
    task_type: str = "passage"
    normalize: bool = True
    auto_chunk: bool = False
    chunk_size: int = 2000
    chunk_overlap: int = 200
    combine_method: str = "average"  # average, weighted, max, first
    return_chunks: bool = False


def build_fastapi(uc: GenerateEmbeddingUC, vdb_usecases: dict = None) -> FastAPI:
    app = FastAPI(
        title="Embeddings + Vector Database Service",
        description="Generate embeddings and store/search vectors",
        version="2.0.0",
    )
    
    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)
    
    # Set up templates
    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/user-docs", response_class=HTMLResponse)
    async def user_docs(request: Request):
        """Interactive user documentation with API testing."""
        return templates.TemplateResponse("user_docs.html", {"request": request})

    @app.get("/postman-collection")
    async def postman_collection():
        """Download Postman collection for API testing."""
        from fastapi.responses import FileResponse
        import os
        
        file_path = "Embeddings_Service.postman_collection.json"
        if os.path.exists(file_path):
            return FileResponse(
                path=file_path,
                media_type="application/json",
                filename="Embeddings_Service.postman_collection.json"
            )
        return {"error": "Postman collection not found"}

    @app.get("/favicon.ico")
    async def favicon():
        """Serve a simple favicon to prevent 404 errors."""
        # Return an SVG favicon with brain emoji
        svg_favicon = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <text y="75" font-size="75">🧠</text>
        </svg>
        """
        return Response(content=svg_favicon, media_type="image/svg+xml")

    @app.get("/health")
    def health():
        return uc.health()
    
    @app.post("/embed/check")
    def check_chunking(req: EmbedReq, auth: AuthContext = Depends(get_current_user)):
        """Check if text would be chunked and get chunking info."""
        if not req.text:
            raise HTTPException(status_code=400, detail="Provide 'text' to check")
        
        info = get_chunking_info(req.text, max_chars=req.chunk_size)
        info["auto_chunk_enabled"] = req.auto_chunk
        info["recommended_action"] = (
            "enable auto_chunk=true" if info["would_be_chunked"] and not req.auto_chunk
            else "text will be chunked" if info["would_be_chunked"]
            else "no chunking needed"
        )
        
        return info

    @app.post("/embed")
    def embed(req: EmbedReq, auth: AuthContext = Depends(get_current_user)):
        items: List[str] = []
        if req.text and req.text.strip():
            items.append(req.text.strip())
        if req.texts:
            items += [t.strip() for t in req.texts if t.strip()]

        if not items:
            raise HTTPException(status_code=400, detail="Provide 'text' or 'texts'")

        # Handle single text with potential chunking
        if len(items) == 1:
            text = items[0]
            text_length = len(text)
            needs_chunking = should_chunk(text) or (req.auto_chunk and text_length > req.chunk_size)
            
            # Check if text is too long and auto_chunk is disabled
            if needs_chunking and not req.auto_chunk:
                # Generate embedding but warn about truncation
                result = uc.embed(text, task_type=req.task_type, normalize=req.normalize)
                result["requested_by"] = auth.username
                result["user_role"] = auth.role
                result["warning"] = f"Text length ({text_length} chars) exceeds model limit (~2048 chars). Consider using auto_chunk=true"
                result["text_length"] = text_length
                result["truncated"] = True
                return result
            
            # Auto-chunking enabled or text is short
            if needs_chunking and req.auto_chunk:
                # Split text into chunks
                chunks = chunk_text(
                    text,
                    max_chars=req.chunk_size,
                    overlap=req.chunk_overlap
                )
                
                # Embed each chunk
                chunk_results = []
                for chunk in chunks:
                    chunk_result = uc.embed(chunk, task_type=req.task_type, normalize=req.normalize)
                    chunk_results.append(chunk_result["embedding"])
                
                # Combine embeddings
                combined_embedding = combine_embeddings(
                    chunk_results,
                    method=req.combine_method
                )
                
                # Get model info from health check
                health_info = uc.health()
                
                # Build response
                response = {
                    "model_id": health_info["model_id"],
                    "dim": health_info["dim"],
                    "embedding": combined_embedding,
                    "requested_by": auth.username,
                    "user_role": auth.role,
                    "text_length": text_length,
                    "was_chunked": True,
                    "num_chunks": len(chunks),
                    "chunk_sizes": [len(c) for c in chunks],
                    "combine_method": req.combine_method,
                }
                
                # Optionally return individual chunk embeddings
                if req.return_chunks:
                    response["chunk_embeddings"] = chunk_results
                    response["chunks"] = chunks
                
                return response
            else:
                # Text is short enough, process normally
                result = uc.embed(text, task_type=req.task_type, normalize=req.normalize)
                result["requested_by"] = auth.username
                result["user_role"] = auth.role
                result["text_length"] = text_length
                result["was_chunked"] = False
                return result
        
        # Multiple texts - process as batch (no chunking for batch mode)
        else:
            res = uc.embed_batch(
                items, task_type=req.task_type, normalize=req.normalize
            )
            return {
                "model_id": res["model_id"],
                "dim": res["dim"],
                "embeddings": [it["embedding"] for it in res["items"]],
                "requested_by": auth.username,
                "user_role": auth.role,
            }

    # Include VDB routes if use cases are provided
    if vdb_usecases:
        vdb_router = build_vdb_router(
            create_project_uc=vdb_usecases["create_project"],
            list_projects_uc=vdb_usecases["list_projects"],
            create_collection_uc=vdb_usecases["create_collection"],
            list_collections_uc=vdb_usecases["list_collections"],
            add_vector_uc=vdb_usecases["add_vector"],
            search_vectors_uc=vdb_usecases["search_vectors"],
            delete_vector_uc=vdb_usecases["delete_vector"],
        )
        app.include_router(vdb_router)
    
    # Include admin UI routes
    admin_router = build_admin_router()
    app.include_router(admin_router)
    
    # Include task queue routes
    app.include_router(task_router)

    return app

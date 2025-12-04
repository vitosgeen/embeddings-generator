from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ...usecases.generate_embedding import GenerateEmbeddingUC
from ...auth import get_current_user
from .vdb_routes import build_vdb_router


class EmbedReq(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None
    task_type: str = "passage"
    normalize: bool = True


def build_fastapi(uc: GenerateEmbeddingUC, vdb_usecases: dict = None) -> FastAPI:
    app = FastAPI(
        title="Embeddings + Vector Database Service",
        description="Generate embeddings and store/search vectors",
        version="2.0.0",
    )
    
    # Set up templates
    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/health")
    def health():
        return uc.health()

    @app.post("/embed")
    def embed(req: EmbedReq, current_user: str = Depends(get_current_user)):
        items: List[str] = []
        if req.text and req.text.strip():
            items.append(req.text.strip())
        if req.texts:
            items += [t.strip() for t in req.texts if t.strip()]

        if not items:
            raise HTTPException(status_code=400, detail="Provide 'text' or 'texts'")

        if len(items) == 1:
            result = uc.embed(items[0], task_type=req.task_type, normalize=req.normalize)
            # Add metadata about the request
            result["requested_by"] = current_user
            return result
        else:
            res = uc.embed_batch(
                items, task_type=req.task_type, normalize=req.normalize
            )
            return {
                "model_id": res["model_id"],
                "dim": res["dim"],
                "embeddings": [it["embedding"] for it in res["items"]],
                "requested_by": current_user,
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

    return app

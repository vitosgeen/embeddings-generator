from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from ...usecases.generate_embedding import GenerateEmbeddingUC
from ...auth import get_current_user


class EmbedReq(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None
    task_type: str = "passage"
    normalize: bool = True
    chunking: bool = True  # Enable chunking by default
    chunk_size: int = 1000
    chunk_overlap: int = 100


class EmbedChunkedReq(BaseModel):
    text: str
    task_type: str = "passage"
    normalize: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 100


def build_fastapi(uc: GenerateEmbeddingUC) -> FastAPI:
    app = FastAPI(title="Embeddings Service (REST)")
    
    # Set up templates
    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})
    
    @app.get("/favicon.ico")
    async def favicon():
        # Simple SVG favicon with brain/AI theme (browser-safe, no emoji)
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="#667eea"/><circle cx="35" cy="45" r="8" fill="white"/><circle cx="65" cy="45" r="8" fill="white"/></svg>'
        return Response(content=svg_content, media_type="image/svg+xml")

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

        # Single text handling
        if len(items) == 1:
            # Use chunking if enabled
            if req.chunking:
                result = uc.embed_chunked(
                    items[0],
                    task_type=req.task_type,
                    normalize=req.normalize,
                    chunk_size=req.chunk_size,
                    chunk_overlap=req.chunk_overlap,
                )
            else:
                result = uc.embed(items[0], task_type=req.task_type, normalize=req.normalize)
            
            # Add metadata about the request
            result["requested_by"] = current_user
            return result
        else:
            # Batch processing (no chunking for multiple texts)
            res = uc.embed_batch(
                items, task_type=req.task_type, normalize=req.normalize
            )
            return {
                "model_id": res["model_id"],
                "dim": res["dim"],
                "embeddings": [it["embedding"] for it in res["items"]],
                "requested_by": current_user,
            }

    @app.post("/embed/chunked")
    def embed_chunked(req: EmbedChunkedReq, current_user: str = Depends(get_current_user)):
        """
        Embed long text by automatically chunking and aggregating.
        Returns aggregated embedding and metadata about chunks.
        """
        if not req.text or not req.text.strip():
            raise HTTPException(status_code=400, detail="Provide 'text'")
        
        result = uc.embed_chunked(
            req.text.strip(),
            task_type=req.task_type,
            normalize=req.normalize,
            chunk_size=req.chunk_size,
            chunk_overlap=req.chunk_overlap,
        )
        result["requested_by"] = current_user
        return result

    return app

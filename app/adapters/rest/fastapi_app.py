from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ...usecases.generate_embedding import GenerateEmbeddingUC


class EmbedReq(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None
    task_type: str = "passage"
    normalize: bool = True


def build_fastapi(uc: GenerateEmbeddingUC) -> FastAPI:
    app = FastAPI(title="Embeddings Service (REST)")

    @app.get("/health")
    def health():
        return uc.health()

    @app.post("/embed")
    def embed(req: EmbedReq):
        items: List[str] = []
        if req.text and req.text.strip():
            items.append(req.text.strip())
        if req.texts:
            items += [t.strip() for t in req.texts if t.strip()]

        if not items:
            raise HTTPException(status_code=400, detail="Provide 'text' or 'texts'")

        if len(items) == 1:
            return uc.embed(items[0], task_type=req.task_type, normalize=req.normalize)
        else:
            res = uc.embed_batch(
                items, task_type=req.task_type, normalize=req.normalize
            )
            return {
                "model_id": res["model_id"],
                "dim": res["dim"],
                "embeddings": [it["embedding"] for it in res["items"]],
            }

    return app

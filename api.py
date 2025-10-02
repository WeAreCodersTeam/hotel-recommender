# api.py
from fastapi import FastAPI, Query, Request
from search_core import Embedder, HotelSearcher

app = FastAPI(title="Search — Embeddings (OpenAI-compatible)")

embedder = Embedder()
searcher = HotelSearcher(embedder, index_backend=None, use_pg=False)

@app.get("/api/search")
def search(request: Request,
           q: str = Query(...),
           user_id: int | None = Query(None),
           top_k: int = Query(10, ge=1, le=50),
           city: str | None = Query(None),
           friends_only: bool = Query(True)):
    # Передаём заголовки, чтобы жюри могло переопределить URL/KEY/MODEL на лету
    return searcher.search_hotels(q, user_id=user_id, top_k=top_k, city=city,
                                  friends_only=friends_only, headers=request.headers)

@app.get("/api/model_info")
def model_info(request: Request):
    # просто возвращаем, что сейчас будет использовано (без секрета)
    cfg = embedder._resolve_cfg(request.headers)
    return {"backend": "openai-compatible", "url": cfg["url"], "model": cfg["model"], "key_set": bool(cfg["key"])}
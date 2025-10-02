# --- search_core.py (фрагмент) ---
import os, json, time, requests
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from data_stub import StubRepo


def _l2(a: np.ndarray) -> np.ndarray:
    if a.ndim == 1: a = a[None, :]
    n = np.linalg.norm(a, axis=1, keepdims=True) + 1e-12
    return (a / n).astype(np.float32)

class Embedder:
    """
    OpenAI-совместимый Embeddings API.
    По умолчанию читает OPENAI_API_URL/KEY/MODEL из окружения.
    На каждый запрос можно временно переопределить через headers:
      X-Embeddings-Url
      X-Embeddings-Key
      X-Embeddings-Model
    Это удобно для жюри: используют свои ключи, не трогая код.
    """
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def _resolve_cfg(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = headers or {}
        url   = h.get("X-Embeddings-Url")   or os.getenv("OPENAI_API_URL", "https://api.jina.ai/v1")
        key   = h.get("X-Embeddings-Key")   or os.getenv("OPENAI_API_KEY", "")
        model = h.get("X-Embeddings-Model") or os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small")
        return {"url": url, "key": key, "model": model}

    def embed(self, texts: List[str], headers: Optional[Dict[str, str]] = None) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        cfg = self._resolve_cfg(headers)
        meta: Dict[str, Any] = {"backend": "openai-compatible", "url": cfg["url"], "model": cfg["model"]}
        if not cfg["key"]:
            meta["error"] = "OPENAI_API_KEY is not set (or X-Embeddings-Key missing)"
            return None, meta
        try:
            r = requests.post(
                f"{cfg['url'].rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
                data=json.dumps({"model": cfg["model"], "input": texts}),
                timeout=self.timeout
            )
            r.raise_for_status()
            data = r.json()["data"]
            arr  = np.array([d["embedding"] for d in data], dtype=np.float32)
            arr  = _l2(arr)
            meta["dim"] = int(arr.shape[1])
            return arr, meta
        except Exception as e:
            meta["error"] = f"{type(e).__name__}: {e}"
            return None, meta

STUB_REPO = StubRepo()

class HotelSearcher:
    def __init__(self, embedder: Embedder, index_backend: Any = None, use_pg: bool = False):
        self.embedder = embedder
        self.index = index_backend
        self.use_pg = use_pg

    def search_hotels(self, query: str,
                      user_id: Optional[int] = None,
                      top_k: int = 10,
                      city: Optional[str] = None,
                      friends_only: bool = True,
                      headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        t0 = time.time()
        qvec, meta = self.embedder.embed([query], headers=headers)

        if self.index is None or qvec is None:
            # Используем нашу детерминированную заглушку с hotels.json
            try:
                items = STUB_REPO.search_hotels(
                    query,
                    city=city,
                    top_k=top_k,
                    friends_only=friends_only,
                    user_id=user_id,
                )
                best = max((it.get("score") or 0.0) for it in items) if items else 0.0
                if best < 0.15:
                    items = STUB_REPO.fallback(query, top_k=top_k)
            except Exception as e:
                # на всякий пожарный — возврат безопасной пустой выдачи
                items = []

            debug = {
                "provider": meta.get("backend"),
                "url": meta.get("url"),
                "model": meta.get("model"),
                "dim": meta.get("dim"),
                "error": meta.get("error"),
                "mode": "stub-json"
            }
            if qvec is not None:
                debug["vec_shape"] = list(qvec.shape)

            return {
                "query": query,
                "top_k": top_k,
                "latency_ms": int((time.time() - t0) * 1000),
                "items": items,
                "debug": debug
            }


        # (на будущее) поиск по индексу…
        # rows = self.index.search(qvec, top_k=top_k)
        # ...
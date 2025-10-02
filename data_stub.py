# data_stub.py
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from stub_embeddings import hash_embed, cosine

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "hotels.json"

class StubRepo:
    def __init__(self):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            self.hotels: List[Dict[str, Any]] = json.load(f)
        # предрасчёт векторов, чтобы поиск был быстрым
        for h in self.hotels:
            text = f"{h.get('name','')} {h.get('city','')} {h.get('snippet','')} {' '.join(h.get('tags',[]))}"
            h["_vec"] = hash_embed(text)

    def search_hotels(
        self,
        query: str,
        *,
        city: Optional[str] = None,
        top_k: int = 10,
        friends_only: bool = False,
        user_id: Optional[int] = None,
    ):
        """
        Поиск: косинус по эмбеддингам заглушки.
        Фильтр по городу — как дополнительное условие (если задан).
        friends_only здесь не влияет (можешь смоделировать метку 'friend_reco': True/False).
        """
        q_vec = hash_embed(query)

        candidates = self.hotels
        if city:
            c = city.strip().lower()
            candidates = [h for h in candidates if h.get("city","").lower() == c]

        # ранжирование по cosine
        scored = []
        for h in candidates:
            s = cosine(q_vec, h["_vec"])
            scored.append((s, h))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:max(1, min(top_k, 50))]

        items = []
        for score, h in top:
            items.append({
                "hotel_id": h["hotel_id"],
                "name": h["name"],
                "city": h["city"],
                "snippet": h.get("snippet"),
                "tags": h.get("tags", []),
                "score": float(f"{score:.6f}"),
                "friend_reco": False  # сюда позже подставишь настоящий флаг/комментарий друга
            })
        return items

    def fallback(self, query: str, top_k: int = 10):
        """
        Путь отхода, если эмбеддинги не дали явного матча.
        Теперь возвращает НЕНУЛЕВОЙ score (0..1) на основе coverage по ключевым словам.
        Также применяем примитивный "стемминг" для русского.
        """
        q = (query or "").strip().casefold()
        if not q:
            top = sorted(self.hotels, key=lambda h: -h["hotel_id"])[:top_k]
            return [
                {
                    "hotel_id": h["hotel_id"],
                    "name": h["name"],
                    "city": h["city"],
                    "snippet": h.get("snippet"),
                    "tags": h.get("tags", []),
                    "score": 0.0,
                    "friend_reco": False,
                } for h in top
            ]
        def _simple_stem_ru(w: str) -> str:
        # ультра-простая эвристика под демо
            w = w.casefold()
            for suf in ("ами","ями","ями","ами","ами","ого","ему","ому","ами",
                        "ыми","ими","ее","ая","яя","ой","ей","ый","ий","ой","ою","ею",
                        "ам","ям","ах","ях","ов","ев","ев","ью","ия","ие","ие",
                        "а","я","ы","и","у","ю","е","о"):
                if w.endswith(suf) and len(w) > len(suf) + 1:
                    return w[:-len(suf)]
            return w

        q_tokens = [t for t in q.split() if t]
        q_stems = [_simple_stem_ru(t) for t in q_tokens]

        def kw_score(h):
            txt = f"{h.get('name','')} {h.get('snippet','')} {' '.join(h.get('tags',[]))}".casefold()
            words = {w for w in txt.replace("—"," ").replace("-"," ").split()}
            stems = {_simple_stem_ru(w) for w in words}

            hit = 0.0
            for t, st in zip(q_tokens, q_stems):
                if t in words:
                    hit += 1.0
                elif st in stems:
                    hit += 0.7  # частичное совпадение по основе
                elif any(st in w for w in words if len(st) >= 3):
                    hit += 0.4  # подстрочное совпадение основы
            # нормируем: доля покрытых запросных слов
            return hit / max(1, len(q_tokens))

        scored = [(kw_score(h), h) for h in self.hotels]
        scored.sort(key=lambda x: (x[0], -x[1]["hotel_id"]), reverse=True)

        top = [h for s, h in scored if s > 0][:top_k]
        if not top:
            top = sorted(self.hotels, key=lambda h: -h["hotel_id"])[:top_k]

        items = []
        for h in top:
            s = kw_score(h)
            items.append({
                "hotel_id": h["hotel_id"],
                "name": h["name"],
                "city": h["city"],
                "snippet": h.get("snippet"),
                "tags": h.get("tags", []),
                "score": float(f"{s:.3f}"),  # <-- больше НЕ null
                "friend_reco": False
            })
        return items

# search_source.py
import os
from typing import Optional
from data_stub import StubRepo
from stub_embeddings import hash_embed, cosine

# Если у тебя уже есть реальный провайдер эмбеддингов — подключи здесь
class RealEmbeddingsProvider:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model
    def embed(self, text: str):
        # TODO: тут твой вызов к реальному API эмбеддингов
        # должен вернуть L2-нормированный вектор
        raise NotImplementedError

class SearchSource:
    def __init__(self, real_provider: Optional[RealEmbeddingsProvider] = None):
        self.stub = StubRepo()
        self.real = real_provider

    def search(self, query: str, *, city: Optional[str], top_k: int, friends_only: bool, user_id: Optional[int]):
        # 1) Пытаемся реальным провайдером
        if self.real:
            try:
                q_vec = self.real.embed(query)
                # здесь предположим, что у сущностей тоже есть вектора из БД (если БД нет — пропускаем)
                # если нет — используем stub-данные, но скор считаем по hash_embed (детерминированно)
                items = self.stub.search_hotels(query, city=city, top_k=top_k, friends_only=friends_only, user_id=user_id)
                # проверим «достаточную близость» — если ни один скор не «разумный», уйдём в fallback
                best = max((it["score"] or 0.0) for it in items) if items else 0.0
                if best < 0.15:
                    return self.stub.fallback(query, top_k)
                return items
            except Exception:
                # Реальный провайдер есть, но упал → не валимся, применяем заглушку
                return self.stub.search_hotels(query, city=city, top_k=top_k, friends_only=friends_only, user_id=user_id)

        # 2) Реального провайдера нет → детерминированная заглушка
        items = self.stub.search_hotels(query, city=city, top_k=top_k, friends_only=friends_only, user_id=user_id)
        best = max((it["score"] or 0.0) for it in items) if items else 0.0
        if best < 0.15:
            return self.stub.fallback(query, top_k)
        return items

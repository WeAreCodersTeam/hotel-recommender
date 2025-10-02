import hashlib
import math

def _l2_norm(v):
    n = math.sqrt(sum(x*x for x in v)) or 1.0
    return [x / n for x in v]

def _mix(vec, token, dim):
    # Символьные 3-граммы с маркерами начала/конца слова
    s = f"^{token}$"
    if len(s) < 3:
        grams = [s]
    else:
        grams = [s[i:i+3] for i in range(len(s) - 3 + 1)]
    for g in grams:
        h = hashlib.sha256(g.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "little") % dim
        sign = 1.0 if (h[4] & 1) == 0 else -1.0
        vec[idx] += sign

def hash_embed(text: str, dim: int = 384):
    """
    Дет. эмбеддинг без внешних сервисов:
    - разбиение на токены по пробелам
    - каждый токен -> сумма хэшей его символьных 3-грамм (с ^ и $)
    - L2-нормировка
    """
    text = (text or "").strip().casefold()
    vec = [0.0] * dim
    if text:
        for tok in text.split():
            _mix(vec, tok, dim)
    return _l2_norm(vec)

def cosine(a, b):
    # a и b — уже L2-нормированные
    return sum(x*y for x, y in zip(a, b))

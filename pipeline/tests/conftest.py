import hashlib
import re
from datetime import datetime, timezone

import numpy as np
import pytest

from prisma.embed import normalize_rows
from prisma.models import Article
from prisma.normalize import article_id, strip_accents

STOP = {"el", "la", "los", "las", "de", "del", "en", "y", "a", "un", "una", "por", "con", "para", "al", "que", "se", "su"}


class FakeEmbedder:
    """Embedding determinista por bolsa de palabras (hash). Solo para probar la lógica."""

    def encode(self, texts):
        out = np.zeros((len(texts), 256), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"\w+", strip_accents(t.lower())):
                if w not in STOP:
                    out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1
        return normalize_rows(out + 1e-6)


@pytest.fixture
def fake():
    return FakeEmbedder()


NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


def mk(source, title, hours_ago=1.0, scope="nacional", url=None, summary=None):
    from datetime import timedelta
    url = url or f"https://{source.lower().replace(' ', '')}.es/{abs(hash(title)) % 10**8}"
    return Article(id=article_id(url), source=source, scope=scope, title=title, url=url,
                   published=NOW - timedelta(hours=hours_ago), summary=summary)

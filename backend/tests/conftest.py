import itertools
import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = tempfile.mkdtemp(prefix="peladex-pytest-")
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test.db")
os.environ["PELADEX_DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["PELADEX_CORS_ORIGINS"] = ""
os.environ["PELADEX_COOKIE_SECURE"] = "false"
os.environ["PELADEX_RATE_LIMIT_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app import ratelimit  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "senha123"
_seq = itertools.count(1)


def unique(prefix: str) -> str:
    return f"{prefix}{next(_seq)}"


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    assert settings.database_url == f"sqlite:///{TEST_DB_PATH}", settings.database_url
    init_db()
    yield TEST_DB_PATH


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class Api:
    def __init__(self, username: str | None = None):
        self.client = TestClient(app)
        self.username = username or unique("user")
        r = self.client.post(
            "/api/auth/register", json={"username": self.username, "password": PASSWORD}
        )
        assert r.status_code == 201, r.text
        self.user_id = r.json()["id"]

    def get(self, url, **kw):
        return self.client.get(url, **kw)

    def post(self, url, **kw):
        return self.client.post(url, **kw)

    def put(self, url, **kw):
        return self.client.put(url, **kw)

    def patch(self, url, **kw):
        return self.client.patch(url, **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, **kw)

    def group(self, name: str | None = None, **extra) -> int:
        r = self.post("/api/groups", json={"name": name or unique("Pelada "), **extra})
        assert r.status_code == 201, r.text
        self.last_group = r.json()
        return r.json()["id"]

    def player(self, group_id: int, name: str | None = None) -> int:
        r = self.post(f"/api/groups/{group_id}/players",
                      json={"name": name or unique("Jogador ")})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def venue(self, group_id: int, name: str | None = None) -> int:
        r = self.post(f"/api/groups/{group_id}/venues", json={"name": name or unique("Campo ")})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def matchday(self, group_id: int, date: str, teams: list[dict],
                 matches: list[dict], **extra):
        body = {"date": date, "teams": teams, "matches": matches, **extra}
        r = self.post(f"/api/groups/{group_id}/matchdays", json=body)
        assert r.status_code == 201, r.text
        return r.json()

    def import_text(self, group_id: int, text: str, **extra):
        return self.post(f"/api/groups/{group_id}/import",
                         json={"text": text, "create_missing_players": True, **extra})


@pytest.fixture
def api() -> Api:
    return Api()


@pytest.fixture
def other_api() -> Api:
    return Api()


@pytest.fixture
def group(api) -> int:
    return api.group()


class QueryCounter:
    def __init__(self):
        self.count = 0
        self.statements: list[str] = []

    def _on_exec(self, conn, cursor, statement, params, context, executemany):
        self.count += 1
        self.statements.append(statement)

    def __enter__(self):
        self.count = 0
        self.statements.clear()
        event.listen(engine, "before_cursor_execute", self._on_exec)
        return self

    def __exit__(self, *exc):
        event.remove(engine, "before_cursor_execute", self._on_exec)
        return False


@pytest.fixture
def queries() -> QueryCounter:
    return QueryCounter()


@pytest.fixture
def rate_limits():
    ratelimit.reset()
    ratelimit.limiter.enabled = True
    yield ratelimit.limiter
    ratelimit.limiter.enabled = False
    ratelimit.reset()


PELADA_TEXT = """2026-09-16
Local: Campo do Ze
BRANCO: golin, galetti, galo, rick, palma, disciplina, mini
VERMELHO: vini, bamma, breno, igor, rod kauer, cesar, beat
AZUL: ney, rod, lusca, pipi, nona, cop, guarino
VERMELHO 0x0 AZUL
BRANCO 0x0 AZUL
BRANCO 1x0 VERMELHO
golin
BRANCO 2x0 AZUL
golin galo
BRANCO 0x0 VERMELHO
VERMELHO 0x0 AZUL
AZUL 0x1 BRANCO
disciplina
BRANCO 1x1 VERMELHO
golin vini
MVP: golin
"""

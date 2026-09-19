from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

BACKEND_ROOT = Path(__file__).resolve().parent.parent

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(BACKEND_ROOT))
    cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    cfg.attributes["configure_logger"] = False
    return cfg


def run_migrations() -> None:
    from alembic import command
    from alembic.script import ScriptDirectory

    from . import models  # noqa: F401

    existing = set(inspect(engine).get_table_names())
    cfg = _alembic_config()

    if "alembic_version" not in existing and existing & set(SQLModel.metadata.tables):
        bases = ScriptDirectory.from_config(cfg).get_bases()
        command.stamp(cfg, bases[0] if len(bases) == 1 else "head")

    command.upgrade(cfg, "head")


def init_db() -> None:
    run_migrations()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

from alembic import command
from sqlalchemy import inspect
from sqlmodel import SQLModel

from app.db import _alembic_config, engine


def test_every_model_table_exists_in_the_migrated_database():
    existing = set(inspect(engine).get_table_names())
    assert set(SQLModel.metadata.tables) <= existing


def test_the_migrations_are_current_with_the_models():
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"compare_type": True, "render_as_batch": True}
        )
        diff = compare_metadata(context, SQLModel.metadata)
    assert diff == [], f"models e migrations divergem: {diff}"


def test_upgrade_is_idempotent():
    command.upgrade(_alembic_config(), "head")

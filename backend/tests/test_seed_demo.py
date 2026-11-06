import re

import pytest
from sqlmodel import Session, SQLModel, create_engine, func, select

from app import models
from app.db import engine
from app.security import verify_password
from scripts import seed_demo


@pytest.fixture
def output(tmp_path, monkeypatch):
    monkeypatch.setattr(seed_demo, "TEXT_OUTPUT", str(tmp_path / "demo.txt"))


def user_count(bind) -> int:
    with Session(bind) as db:
        return db.exec(select(func.count()).select_from(models.User)).one()


def test_a_plain_run_only_reports(output, capsys):
    assert seed_demo.APPLY is False
    seed_demo.main()
    assert "nothing written" in capsys.readouterr().out


def test_it_refuses_a_database_that_already_has_users(api, output, monkeypatch):
    monkeypatch.setattr(seed_demo, "APPLY", True)
    users = user_count(engine)
    with pytest.raises(SystemExit):
        seed_demo.main()
    assert user_count(engine) == users


def test_an_empty_database_gets_a_random_password_printed_once(tmp_path, output, monkeypatch,
                                                                capsys):
    fresh = create_engine(f"sqlite:///{tmp_path / 'seed.db'}")
    monkeypatch.setattr(seed_demo, "engine", fresh)
    monkeypatch.setattr(seed_demo, "init_db", lambda: SQLModel.metadata.create_all(fresh))
    monkeypatch.setattr(seed_demo, "APPLY", True)

    seed_demo.main()

    out = capsys.readouterr().out
    password = re.search(rf"login: {seed_demo.OWNER_USERNAME} / (\S+)", out).group(1)
    assert password != "pelada123"
    assert len(password) >= 16
    assert out.count(password) == 1
    with Session(fresh) as db:
        owner = db.exec(select(models.User)).one()
        assert verify_password(password, owner.password_hash)
        assert db.exec(select(func.count()).select_from(models.Matchday)).one() > 0

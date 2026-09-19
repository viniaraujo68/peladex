from datetime import date

from app import parser
from tests.conftest import PELADA_TEXT


def test_parses_the_real_notation():
    result = parser.parse(PELADA_TEXT)
    assert result.ok
    day = result.matchdays[0]
    assert day.date == date(2026, 9, 16)
    assert day.venue == "Campo do Ze"
    assert day.mvp == "golin"
    assert [t.name for t in day.teams] == ["BRANCO", "VERMELHO", "AZUL"]
    assert all(len(t.players) == 7 for t in day.teams)
    assert len(day.matches) == 8
    assert len(result.new_players) == 21


def test_rejects_a_team_playing_itself():
    text = "2026-09-16\nAZUL: a\nBRANCO: b\nAZUL 0x0 AZUL\n"
    result = parser.parse(text)
    assert not result.ok
    assert any(i.code == "same_team_twice" for i in result.issues)


def test_rejects_an_undeclared_team():
    text = "2026-09-16\nAZUL: a\nBRANCO: b\nVERDE 1x0 AZUL\n"
    result = parser.parse(text)
    assert not result.ok
    assert any(i.code == "unknown_team" for i in result.issues)


def test_rejects_a_player_on_two_teams():
    text = "2026-09-16\nAZUL: a, b\nBRANCO: b, c\n"
    result = parser.parse(text)
    assert not result.ok
    assert any(i.code == "player_in_two_teams" for i in result.issues)


def test_distinguishes_a_name_that_prefixes_another():
    text = (
        "2026-09-16\n"
        "VERMELHO: rod kauer, cesar\n"
        "AZUL: rod, ney\n"
        "VERMELHO 1x0 AZUL\n"
        "rod kauer\n"
        "AZUL 1x0 VERMELHO\n"
        "rod\n"
    )
    result = parser.parse(text)
    assert result.ok
    first, second = result.matchdays[0].matches
    assert [g.player for g in first.goals] == ["rod kauer"]
    assert [g.player for g in second.goals] == ["rod"]


def test_own_goal_marker_binds_before_or_after_the_name():
    text = (
        "2026-09-16\n"
        "BRANCO: golin\n"
        "AZUL: ney, rod\n"
        "BRANCO 1x0 AZUL: (gc) ney\n"
        "BRANCO 1x0 AZUL\n"
        "rod (gc)\n"
    )
    result = parser.parse(text)
    assert result.ok
    for match in result.matchdays[0].matches:
        assert len(match.goals) == 1
        goal = match.goals[0]
        assert goal.own_goal is True
        assert goal.team == "BRANCO"


def test_multiplier_expands_into_separate_goals():
    text = "2026-09-16\nBRANCO: golin\nAZUL: ney\nBRANCO 3x0 AZUL: golin x2, golin\n"
    result = parser.parse(text)
    assert result.ok
    assert len(result.matchdays[0].matches[0].goals) == 3


def test_warns_when_scorers_do_not_add_up_but_still_parses():
    text = "2026-09-16\nBRANCO: golin\nAZUL: ney\nBRANCO 3x0 AZUL: golin\n"
    result = parser.parse(text)
    assert result.ok
    assert any(i.code == "goal_count_mismatch" for i in result.issues)


def test_several_matchdays_in_one_text_inherit_the_year():
    text = (
        "2026-09-16\nBRANCO: a\nAZUL: b\nBRANCO 1x0 AZUL: a\n"
        "---\n"
        "23/09\nBRANCO: a\nAZUL: b\nBRANCO 0x1 AZUL: b\n"
    )
    result = parser.parse(text)
    assert result.ok
    assert [d.date for d in result.matchdays] == [date(2026, 9, 16), date(2026, 9, 23)]


def test_accepts_alternative_date_and_score_spellings():
    text = "16/09/2026\nBRANCO: a\nAZUL: b\nBRANCO 2 - 1 AZUL\n"
    result = parser.parse(text)
    assert result.ok
    day = result.matchdays[0]
    assert day.date == date(2026, 9, 16)
    assert (day.matches[0].home_score, day.matches[0].away_score) == (2, 1)


def test_comments_and_blank_lines_are_ignored():
    text = "# a pelada\n\n2026-09-16\nBRANCO: a\nAZUL: b\n// nada aqui\nBRANCO 1x0 AZUL: a\n"
    assert parser.parse(text).ok


def test_empty_text_is_an_error():
    assert not parser.parse("   \n\n").ok

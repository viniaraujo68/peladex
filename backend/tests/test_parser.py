import time
from datetime import date

import pytest

from app import parser
from tests.conftest import PELADA_TEXT


def test_parses_the_real_notation():
    result = parser.parse(PELADA_TEXT)
    assert result.ok
    day = result.matchdays[0]
    assert day.date == date(2026, 9, 16)
    assert day.venue == "Campo do Ze"
    assert day.mvp == "golin"
    assert [t.name for t in day.teams] == ["branco", "vermelho", "azul"]
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
        assert goal.team == "branco"


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


def test_case_does_not_matter_and_names_come_out_lowercase():
    text = (
        "2026-09-16\n"
        "Azul: Golin, RICK\n"
        "BRANCO: Vini, bamma\n"
        "azul 2x1 Branco: GOLIN, Rick (golin)\n"
        "MVP: GoLiN\n"
    )
    result = parser.parse(text)
    assert result.ok
    day = result.matchdays[0]
    assert [t.name for t in day.teams] == ["azul", "branco"]
    assert day.teams[0].players == ["golin", "rick"]
    assert day.mvp == "golin"
    assert sorted(result.new_players) == ["bamma", "golin", "rick", "vini"]
    goals = day.matches[0].goals
    assert [(g.player, g.team, g.assist) for g in goals] == [
        ("golin", "azul", None),
        ("rick", "azul", "golin"),
    ]


def test_an_existing_player_matches_regardless_of_case():
    text = "2026-09-16\nAZUL: GOLIN\nBRANCO: vini\n"
    result = parser.parse(text, known_players=["golin"])
    assert result.ok
    assert result.matchdays[0].teams[0].players == ["golin"]
    assert result.new_players == ["vini"]


def goal_count_text(annotation: str) -> str:
    return f"2026-09-16\nBRANCO: golin\nAZUL: ney\nBRANCO 1x0 AZUL\ngolin({annotation})\n"


@pytest.mark.parametrize("annotation", ["1000000", "9" * 4301, "\u1369", "\u0661\u0662"],
                         ids=["seven_digits", "4301_digits", "ethiopic_digit", "arabic_digits"])
def test_a_goal_count_annotation_must_be_one_or_two_ascii_digits(annotation):
    result = parser.parse(goal_count_text(annotation))
    assert not result.ok
    assert [i.code for i in result.issues if i.severity == "error"] == ["bad_goal_count"]
    assert len(result.matchdays[0].matches[0].goals) <= 1


def test_a_two_digit_goal_count_is_still_accepted():
    text = "2026-09-16\nBRANCO: golin\nAZUL: ney\nBRANCO 12x0 AZUL\ngolin (12)\n"
    result = parser.parse(text)
    assert result.ok
    assert len(result.matchdays[0].matches[0].goals) == 12


def test_more_goals_than_the_score_is_an_error():
    result = parser.parse("2026-09-16\nBRANCO: golin\nAZUL: ney\nBRANCO 1x0 AZUL: golin, golin\n")
    assert not result.ok
    assert any(i.code == "too_many_goals" and i.severity == "error" for i in result.issues)


def test_multipliers_cannot_inflate_the_goal_list_past_the_score():
    text = "2026-09-16\nBRANCO: golin\nAZUL: ney\nBRANCO 1x0 AZUL: " + "golin x99, " * 5000
    result = parser.parse(text)
    assert not result.ok
    assert len(result.matchdays[0].matches[0].goals) <= 1


def test_a_comma_free_team_line_matches_known_names_up_to_the_token_cap():
    eight = "a b c d e f g h"
    nine = "i j k l m n o p q"
    text = f"2026-09-16\nAZUL: {eight}\nBRANCO: {nine}\n"
    result = parser.parse(text, known_players=[eight, nine])
    azul, branco = result.matchdays[0].teams
    assert azul.players == [eight]
    assert branco.players == nine.split()


@pytest.mark.parametrize("text,code", [
    ("2026-09-16\nAZUL: " + "x" * 81 + ", ana\nBRANCO: bia\n", "name_too_long"),
    ("2026-09-16\nLocal: " + "c" * 81 + "\nAZUL: ana\nBRANCO: bia\n", "name_too_long"),
    ("2026-09-16 @ " + "c" * 81 + "\nAZUL: ana\nBRANCO: bia\n", "name_too_long"),
    ("2026-09-16\n" + "t" * 41 + ": ana\nBRANCO: bia\n", "team_name_too_long"),
    ("2026-09-16\n: ana\nBRANCO: bia\n", "missing_team_name"),
    ("2026-09-16\nAZUL: ana\nBRANCO: bia\nObs: " + "n" * 2001 + "\n", "notes_too_long"),
], ids=["player_name", "venue_line", "venue_on_date", "team_name", "empty_team_name", "notes"])
def test_values_past_the_write_limits_are_import_errors(text, code):
    result = parser.parse(text)
    assert not result.ok
    assert code in {i.code for i in result.issues if i.severity == "error"}


def test_a_team_cannot_pass_the_player_cap():
    names = ", ".join(f"p{i}" for i in range(parser.MAX_TEAM_PLAYERS + 1))
    result = parser.parse(f"2026-09-16\nAZUL: {names}\nBRANCO: bia\n")
    assert not result.ok
    assert any(i.code == "too_many_players" for i in result.issues)
    assert len(result.matchdays[0].teams[0].players) == parser.MAX_TEAM_PLAYERS


def test_a_matchday_cannot_pass_the_team_cap():
    teams = "\n".join(f"t{i}: p{i}" for i in range(parser.MAX_MATCHDAY_TEAMS + 1))
    result = parser.parse(f"2026-09-16\n{teams}\n")
    assert not result.ok
    assert any(i.code == "too_many_teams" for i in result.issues)
    assert len(result.matchdays[0].teams) == parser.MAX_MATCHDAY_TEAMS


def test_runs_of_whitespace_inside_a_line_are_collapsed():
    text = "2026-09-16\nAZUL:\t rod   kauer ,  ney\nBRANCO: bia\nAZUL   1  x  0\t BRANCO\n"
    result = parser.parse(text)
    assert result.ok
    assert result.matchdays[0].teams[0].players == ["rod kauer", "ney"]
    assert len(result.matchdays[0].matches) == 1


def test_the_issue_list_is_capped_without_hiding_errors():
    result = parser.parse("2026-09-16\nAZUL: ana\nBRANCO: bia\n" + "zz\n" * 1000)
    assert len(result.issues) == parser.MAX_ISSUES + 1
    summary = result.issues[-1]
    assert summary.code == "too_many_issues"
    assert summary.severity == parser.SEVERITY_ERROR
    assert not result.ok


def test_a_capped_list_of_warnings_stays_a_warning():
    scorers = ", ".join(f"x{i}" for i in range(500))
    result = parser.parse(f"2026-09-16\nAZUL: ana\nBRANCO: bia\nAZUL 0x0 BRANCO: {scorers}\n")
    assert result.issues[-1].code == "too_many_issues"
    assert result.issues[-1].severity == parser.SEVERITY_WARNING
    assert result.ok


def test_issue_text_and_message_are_clipped():
    result = parser.parse("2026-09-16\nAZUL: ana\nBRANCO: bia\n" + "z" * 50_000 + "\n")
    issue = next(i for i in result.issues if i.code == "unexpected_line")
    assert len(issue.text) <= parser.MAX_ISSUE_TEXT_LENGTH
    assert len(issue.message) <= parser.MAX_ISSUE_TEXT_LENGTH


SINGLE_LINE_BUDGET_SECONDS = 2.0
LONG_LINES = {
    "team_tokens": "VERDE: " + "a " * 100_000,
    "team_commas": "VERDE: " + "a," * 100_000,
    "team_distinct": "VERDE: " + " ".join(f"p{i}" for i in range(40_000)),
    "goal_tokens": "golin " * 40_000,
    "whitespace": "AZUL" + " \t" * 100_000 + "1",
    "venue_markers": "Local:" + " @" * 100_000,
    "annotations": "golin(99)" * 25_000,
}


@pytest.mark.timing
@pytest.mark.parametrize("name", list(LONG_LINES))
def test_a_200k_single_line_parses_fast(name):
    head = "2026-09-16\nBRANCO: golin\nAZUL: ney\nBRANCO 1x0 AZUL\n"
    text = (head + LONG_LINES[name])[:200_000]
    known = ["a b c d e f g h", "golin", "ney"] + [f"k{i}" for i in range(2000)]
    start = time.perf_counter()
    result = parser.parse(text, known_players=known)
    assert time.perf_counter() - start < SINGLE_LINE_BUDGET_SECONDS
    assert len(result.issues) <= parser.MAX_ISSUES + 1

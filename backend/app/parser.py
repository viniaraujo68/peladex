from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

RESERVED_VENUE = {"local", "campo", "onde", "quadra"}
RESERVED_MVP = {"mvp", "craque", "destaque"}
RESERVED_DATE = {"data", "dia"}
RESERVED_NOTES = {"obs", "nota", "notas", "observacao", "observacoes"}
RESERVED = RESERVED_VENUE | RESERVED_MVP | RESERVED_DATE | RESERVED_NOTES

SEPARATOR_RE = re.compile(r"^[-*=_]{3,}$")
MATCH_RE = re.compile(
    r"^(?P<home>.+?)\s+(?P<hs>\d{1,2})\s*(?:[xX×]|-|:)\s*(?P<as>\d{1,2})\s+(?P<away>.+?)$"
)
OWN_GOAL_RE = re.compile(r"\(\s*(?:gc|ct|contra)\s*\)", re.IGNORECASE)
MULT_PREFIX_RE = re.compile(r"^(\d{1,2})\s*[xX×]\s*(.+)$")
MULT_SUFFIX_RE = re.compile(r"^(.+?)\s*(?:[xX×]\s*(\d{1,2})|\((\d{1,2})\))$")

ISO_DATE_RE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
BR_DATE_RE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?$")


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped)


@dataclass
class ParseIssue:
    line: int
    severity: str
    code: str
    message: str
    text: str = ""


@dataclass
class ParsedGoal:
    player: str
    team: str
    own_goal: bool = False


@dataclass
class ParsedMatch:
    line: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    goals: list[ParsedGoal] = field(default_factory=list)


@dataclass
class ParsedTeam:
    line: int
    name: str
    players: list[str] = field(default_factory=list)


@dataclass
class ParsedMatchday:
    line: int
    date: date | None = None
    raw_date: str = ""
    venue: str | None = None
    mvp: str | None = None
    notes: str = ""
    teams: list[ParsedTeam] = field(default_factory=list)
    matches: list[ParsedMatch] = field(default_factory=list)


@dataclass
class ParseResult:
    matchdays: list[ParsedMatchday] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    new_players: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == SEVERITY_ERROR for i in self.issues)


def parse_date_token(token: str, default_year: int | None = None) -> date | None:
    token = token.strip()
    iso = ISO_DATE_RE.match(token)
    if iso:
        year, month, day = (int(g) for g in iso.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    br = BR_DATE_RE.match(token)
    if br:
        day, month, raw_year = br.group(1), br.group(2), br.group(3)
        if raw_year is None:
            year = default_year or date.today().year
        else:
            year = int(raw_year)
            if year < 100:
                year += 2000
        try:
            return date(year, int(month), int(day))
        except ValueError:
            return None
    return None


def _strip_own_goal(chunk: str) -> tuple[str, bool]:
    cleaned = OWN_GOAL_RE.sub(" ", chunk)
    return re.sub(r"\s+", " ", cleaned).strip(), cleaned != chunk


def _strip_multiplier(chunk: str) -> tuple[str, int]:
    prefix = MULT_PREFIX_RE.match(chunk)
    if prefix:
        return prefix.group(2).strip(), int(prefix.group(1))
    suffix = MULT_SUFFIX_RE.match(chunk)
    if suffix:
        count = suffix.group(2) or suffix.group(3)
        return suffix.group(1).strip(), int(count)
    return chunk, 1


def _greedy_split(text: str, lookup: dict[str, str]) -> list[str]:
    tokens = text.split()
    chunks: list[str] = []
    i = 0
    while i < len(tokens):
        matched = False
        for size in range(len(tokens) - i, 0, -1):
            candidate = " ".join(tokens[i : i + size])
            if normalize(candidate) in lookup:
                chunks.append(candidate)
                i += size
                matched = True
                break
        if not matched:
            chunks.append(tokens[i])
            i += 1
    return chunks


def split_names(text: str, lookup: dict[str, str]) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if "," in text or ";" in text or "/" in text:
        return [part.strip() for part in re.split(r"[,;/]", text) if part.strip()]
    return _greedy_split(text, lookup)


class _MatchdayBuilder:
    def __init__(self, line: int, known_players: dict[str, str]):
        self.day = ParsedMatchday(line=line)
        self.known = known_players
        self.roster: dict[str, str] = {}
        self.team_of: dict[str, str] = {}
        self.issues: list[ParseIssue] = []
        self.new_players: list[str] = []

    def issue(self, line: int, severity: str, code: str, message: str, text: str = "") -> None:
        self.issues.append(ParseIssue(line, severity, code, message, text))

    def canonical_player(self, raw: str) -> str:
        key = normalize(raw)
        if key in self.roster:
            return self.roster[key]
        if key in self.known:
            return self.known[key]
        return raw.strip()

    def add_team(self, line: int, name: str, body: str, text: str) -> None:
        name = name.strip()
        if any(normalize(t.name) == normalize(name) for t in self.day.teams):
            self.issue(line, SEVERITY_ERROR, "duplicate_team",
                       f"O time “{name}” foi escalado duas vezes no mesmo dia.", text)
            return
        team = ParsedTeam(line=line, name=name)
        for raw in split_names(body, self.known):
            player = self.canonical_player(raw)
            key = normalize(player)
            if not key:
                continue
            if key in self.team_of:
                self.issue(line, SEVERITY_ERROR, "player_in_two_teams",
                           f"“{player}” está escalado em {self.team_of[key]} e em {name}.", text)
                continue
            if key in team_keys(team):
                self.issue(line, SEVERITY_WARNING, "duplicate_player",
                           f"“{player}” aparece duas vezes em {name}.", text)
                continue
            if key not in self.known and key not in self.roster:
                self.new_players.append(player)
            self.roster[key] = player
            self.team_of[key] = name
            team.players.append(player)
        self.day.teams.append(team)

    def find_team(self, raw: str) -> str | None:
        key = normalize(raw)
        for team in self.day.teams:
            if normalize(team.name) == key:
                return team.name
        return None

    def team_players(self, name: str) -> list[str]:
        for team in self.day.teams:
            if team.name == name:
                return team.players
        return []

    def add_match(self, line: int, home: str, hs: int, away: str, away_score: int,
                  goals_text: str, text: str) -> ParsedMatch | None:
        home_name = self.find_team(home)
        away_name = self.find_team(away)
        if home_name is None or away_name is None:
            missing = home if home_name is None else away
            self.issue(line, SEVERITY_ERROR, "unknown_team",
                       f"O time “{missing.strip()}” não foi escalado neste dia.", text)
            return None
        if home_name == away_name:
            self.issue(line, SEVERITY_ERROR, "same_team_twice",
                       f"{home_name} não pode jogar contra ele mesmo.", text)
            return None
        match = ParsedMatch(line=line, home_team=home_name, away_team=away_name,
                            home_score=hs, away_score=away_score)
        self.day.matches.append(match)
        if goals_text.strip():
            self.add_goals(line, match, goals_text, text)
        return match

    def add_goals(self, line: int, match: ParsedMatch, text_body: str, text: str) -> None:
        pool: dict[str, str] = {}
        for name in self.team_players(match.home_team) + self.team_players(match.away_team):
            pool[normalize(name)] = name

        entries: list[dict] = []
        pending_own_goal = False
        for chunk in split_names(text_body, pool):
            name_part, marker = _strip_own_goal(chunk)
            if not name_part:
                if marker:
                    if entries:
                        entries[-1]["own_goal"] = True
                    else:
                        pending_own_goal = True
                continue
            name_part, count = _strip_multiplier(name_part)
            if not name_part:
                continue
            entries.append({"name": name_part, "count": count,
                            "own_goal": marker or pending_own_goal})
            pending_own_goal = False

        for entry in entries:
            name_part = entry["name"]
            key = normalize(name_part)
            resolved = pool.get(key)
            if resolved is None:
                resolved = self.roster.get(key)
                if resolved is None:
                    self.issue(line, SEVERITY_WARNING, "unknown_scorer",
                               f"\u201c{name_part}\u201d marcou gol mas n\u00e3o est\u00e1 escalado neste dia.", text)
                    continue
                self.issue(line, SEVERITY_WARNING, "scorer_off_match",
                           f"\u201c{resolved}\u201d marcou em {match.home_team} x {match.away_team}, "
                           f"mas joga em {self.team_of.get(key, '?')}.", text)
            scorer_team = self.team_of.get(normalize(resolved), match.home_team)
            if entry["own_goal"]:
                credited = match.away_team if scorer_team == match.home_team else match.home_team
            else:
                credited = scorer_team
            for _ in range(entry["count"]):
                match.goals.append(ParsedGoal(player=resolved, team=credited,
                                              own_goal=entry["own_goal"]))

    def finish(self) -> ParsedMatchday:
        if self.day.date is None:
            self.issue(self.day.line, SEVERITY_ERROR, "missing_date",
                       "Este dia não tem data. Comece o bloco com uma linha de data.")
        if not self.day.teams:
            self.issue(self.day.line, SEVERITY_ERROR, "no_teams",
                       "Nenhum time foi escalado neste dia.")
        for match in self.day.matches:
            scored = {match.home_team: 0, match.away_team: 0}
            for goal in match.goals:
                if goal.team in scored:
                    scored[goal.team] += 1
            expected = match.home_score + match.away_score
            if match.goals and len(match.goals) != expected:
                self.issue(match.line, SEVERITY_WARNING, "goal_count_mismatch",
                           f"{match.home_team} {match.home_score}x{match.away_score} "
                           f"{match.away_team}: {expected} gol(s) no placar, "
                           f"{len(match.goals)} artilheiro(s) anotado(s).")
            elif match.goals and (scored[match.home_team] != match.home_score
                                  or scored[match.away_team] != match.away_score):
                self.issue(match.line, SEVERITY_WARNING, "goal_side_mismatch",
                           f"{match.home_team} {match.home_score}x{match.away_score} "
                           f"{match.away_team}: os artilheiros somam "
                           f"{scored[match.home_team]}x{scored[match.away_team]}.")
        if self.day.mvp:
            key = normalize(self.day.mvp)
            if key not in self.team_of:
                self.issue(self.day.line, SEVERITY_WARNING, "mvp_not_playing",
                           f"O MVP “{self.day.mvp}” não está escalado neste dia.")
        return self.day


def team_keys(team: ParsedTeam) -> set[str]:
    return {normalize(p) for p in team.players}


def parse(text: str, known_players: list[str] | None = None,
          default_year: int | None = None) -> ParseResult:
    known = {normalize(name): name for name in (known_players or [])}
    result = ParseResult()
    builder: _MatchdayBuilder | None = None
    last_match: ParsedMatch | None = None
    year_hint = default_year

    def close() -> None:
        nonlocal builder, last_match, year_hint
        if builder is None:
            return
        finished = builder.finish()
        if finished.date is not None:
            year_hint = finished.date.year
        result.matchdays.append(finished)
        result.issues.extend(builder.issues)
        for name in builder.new_players:
            if name not in result.new_players:
                result.new_players.append(name)
        builder = None
        last_match = None

    for index, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if SEPARATOR_RE.match(line):
            close()
            continue

        as_date = parse_date_token(line.split()[0], year_hint) if line.split() else None
        if as_date is not None and ":" not in line:
            close()
            builder = _MatchdayBuilder(index, known)
            builder.day.date = as_date
            builder.day.raw_date = line
            continue

        head, sep, tail = line.partition(":")
        head_key = normalize(head)

        if sep and head_key in RESERVED:
            if builder is None:
                builder = _MatchdayBuilder(index, known)
            value = tail.strip()
            if head_key in RESERVED_VENUE:
                builder.day.venue = value or None
            elif head_key in RESERVED_MVP:
                builder.day.mvp = value or None
            elif head_key in RESERVED_DATE:
                parsed = parse_date_token(value, year_hint)
                if parsed is None:
                    builder.issue(index, SEVERITY_ERROR, "bad_date",
                                  f"Não consegui ler a data “{value}”.", line)
                else:
                    builder.day.date = parsed
                    builder.day.raw_date = value
            else:
                builder.day.notes = (builder.day.notes + "\n" + value).strip()
            continue

        match_on_head = MATCH_RE.match(head) if sep else None
        match_on_line = MATCH_RE.match(line) if not sep else None

        if sep and match_on_head is None:
            if builder is None:
                builder = _MatchdayBuilder(index, known)
            builder.add_team(index, head, tail, line)
            last_match = None
            continue

        hit = match_on_head or match_on_line
        if hit:
            if builder is None:
                builder = _MatchdayBuilder(index, known)
            last_match = builder.add_match(
                index, hit.group("home"), int(hit.group("hs")),
                hit.group("away"), int(hit.group("as")),
                tail if match_on_head else "", line,
            )
            continue

        if builder is not None and last_match is not None:
            builder.add_goals(index, last_match, line, line)
            continue

        if builder is None:
            result.issues.append(ParseIssue(index, SEVERITY_ERROR, "unexpected_line",
                                            "Linha fora de um dia de pelada.", line))
        else:
            builder.issue(index, SEVERITY_ERROR, "unexpected_line",
                          "Não entendi esta linha.", line)

    close()

    if not result.matchdays:
        result.issues.append(ParseIssue(0, SEVERITY_ERROR, "empty",
                                        "Nenhum dia de pelada encontrado no texto."))
    result.issues.sort(key=lambda i: (i.line, i.severity))
    return result

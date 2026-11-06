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

MAX_NAME_TOKENS = 8
MAX_NAME_LENGTH = 80
MAX_TEAM_NAME_LENGTH = 40
MAX_TEAM_PLAYERS = 40
MAX_MATCHDAY_TEAMS = 20
MAX_NOTES_LENGTH = 2000
MAX_ISSUES = 200
MAX_ISSUE_TEXT_LENGTH = 200

SEPARATOR_RE = re.compile(r"^[-*=_]{3,}$")
MATCH_RE = re.compile(
    r"^(?P<home>.+?)\s+(?P<hs>\d{1,2})\s*(?:[xX×]|-)\s*(?P<as>\d{1,2})\s+(?P<away>.+?)$"
)
OWN_GOAL_WORDS = {"gc", "ct", "contra", "og", "gol contra"}
VENUE_SPLIT_RE = re.compile(r"\s+@\s*(?P<venue>.+)$")
MULT_PREFIX_RE = re.compile(r"^(\d{1,2})\s*[xX×]\s*(.+)$")
MULT_SUFFIX_RE = re.compile(r"^(.+?)\s*(?:[xX×]\s*(\d{1,2})|\((\d{1,2})\))$")
BARE_MULT_RE = re.compile(r"^[xX×]\s*(\d{1,2})$")
GOAL_COUNT_RE = re.compile(r"[0-9]{1,2}")
WHITESPACE_RE = re.compile(r"\s+")

ISO_DATE_RE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
BR_DATE_RE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?$")


def display_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", stripped)


def _clip(value: str) -> str:
    if len(value) <= MAX_ISSUE_TEXT_LENGTH:
        return value
    return value[: MAX_ISSUE_TEXT_LENGTH - 1] + "…"


ISSUE_MESSAGES = {
    "venue_name_too_long": "The venue name is longer than {limit} characters.",
    "missing_team_name": "The team name is missing before the colon.",
    "team_name_too_long": "The team name is longer than {limit} characters.",
    "duplicate_team": "Team \u201c{team}\u201d was lined up twice on the same day.",
    "too_many_teams": "A matchday takes at most {limit} teams.",
    "name_too_long": "A player name in {team} is longer than {limit} characters.",
    "player_in_two_teams": "\u201c{player}\u201d is lined up in {team} and in {other_team}.",
    "duplicate_player": "\u201c{player}\u201d appears twice in {team}.",
    "too_many_players": "Team \u201c{team}\u201d has more than {limit} players.",
    "unknown_team": "Team \u201c{team}\u201d was not lined up on this day.",
    "same_team_twice": "{team} cannot play against itself.",
    "bad_goal_count": "\u201c{value}\u201d is not a valid goal count.",
    "stray_assist": "\u201c{value}\u201d looks like an assist but does not follow a scorer.",
    "unknown_scorer": "\u201c{player}\u201d scored but is not lined up on this day.",
    "scorer_off_match": "\u201c{player}\u201d scored in {home} x {away}, but plays for {team}.",
    "too_many_goals": "{home} {home_score}x{away_score} {away}: more goals were written than the score.",
    "own_goal_assist": "An own goal by \u201c{player}\u201d cannot have an assist; the one by \u201c{assist}\u201d was ignored.",
    "unknown_assist": "\u201c{player}\u201d assisted but is not lined up on this day.",
    "self_assist": "\u201c{player}\u201d cannot assist their own goal.",
    "assist_other_team": "\u201c{assist}\u201d does not play on the same team as \u201c{player}\u201d, so the assist was ignored.",
    "missing_date": "This matchday has no date. Start the block with a date line.",
    "no_teams": "No team was lined up on this day.",
    "notes_too_long": "The matchday notes are longer than {limit} characters.",
    "goal_count_mismatch": "{home} {home_score}x{away_score} {away}: {expected} goal(s) in the score, {scored} scorer(s) written.",
    "goal_side_mismatch": "{home} {home_score}x{away_score} {away}: the scorers add up to {home_scored}x{away_scored}.",
    "mvp_not_playing": "MVP \u201c{player}\u201d is not lined up on this day.",
    "bad_date": "Could not read the date \u201c{value}\u201d.",
    "outside_matchday": "Line outside a matchday.",
    "unexpected_line": "Could not understand this line.",
    "empty": "No matchday found in the text.",
    "too_many_issues": "And {count} more problem(s) from here on.",
}


@dataclass
class ParseIssue:
    line: int
    severity: str
    code: str
    text: str = ""
    params: dict[str, str | int] = field(default_factory=dict)
    message: str = field(init=False)

    def __post_init__(self) -> None:
        self.params = {k: _clip(v) if isinstance(v, str) else v for k, v in self.params.items()}
        self.message = _clip(ISSUE_MESSAGES[self.code].format(**self.params))
        self.text = _clip(self.text)


@dataclass
class ParsedGoal:
    player: str
    team: str
    own_goal: bool = False
    assist: str | None = None


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


def split_annotations(text: str) -> list[tuple[str, str | None]]:
    parts: list[tuple[str, str | None]] = []
    buffer = ""
    index = 0
    while index < len(text):
        char = text[index]
        if char == "(":
            close = text.find(")", index)
            if close == -1:
                buffer += text[index:]
                break
            parts.append((buffer, text[index + 1 : close]))
            buffer = ""
            index = close + 1
        else:
            buffer += char
            index += 1
    if buffer.strip():
        parts.append((buffer, None))
    return parts


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
    keys = [normalize(token).strip() for token in tokens]
    chunks: list[str] = []
    i = 0
    while i < len(tokens):
        for size in range(min(MAX_NAME_TOKENS, len(tokens) - i), 0, -1):
            if " ".join(key for key in keys[i : i + size] if key) in lookup:
                chunks.append(" ".join(tokens[i : i + size]))
                i += size
                break
        else:
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


def _score_params(match: ParsedMatch) -> dict[str, str | int]:
    return {"home": match.home_team, "away": match.away_team,
            "home_score": match.home_score, "away_score": match.away_score}


class _MatchdayBuilder:
    def __init__(self, line: int, known_players: dict[str, str]):
        self.day = ParsedMatchday(line=line)
        self.known = known_players
        self.roster: dict[str, str] = {}
        self.team_of: dict[str, str] = {}
        self.issues: list[ParseIssue] = []
        self.new_players: list[str] = []

    def issue(self, line: int, severity: str, code: str, text: str = "", **params: str | int) -> None:
        self.issues.append(ParseIssue(line, severity, code, text, params))

    def canonical_player(self, raw: str) -> str:
        key = normalize(raw)
        if key in self.roster:
            return self.roster[key]
        if key in self.known:
            return self.known[key]
        return display_name(raw)

    def set_venue(self, line: int, value: str, text: str) -> None:
        if len(value) > MAX_NAME_LENGTH:
            self.issue(line, SEVERITY_ERROR, "venue_name_too_long", text, limit=MAX_NAME_LENGTH)
            return
        self.day.venue = value or None

    def add_team(self, line: int, name: str, body: str, text: str) -> None:
        name = display_name(name)
        if not name:
            self.issue(line, SEVERITY_ERROR, "missing_team_name", text)
            return
        if len(name) > MAX_TEAM_NAME_LENGTH:
            self.issue(line, SEVERITY_ERROR, "team_name_too_long", text,
                       limit=MAX_TEAM_NAME_LENGTH)
            return
        if any(normalize(t.name) == normalize(name) for t in self.day.teams):
            self.issue(line, SEVERITY_ERROR, "duplicate_team", text, team=name)
            return
        if len(self.day.teams) >= MAX_MATCHDAY_TEAMS:
            self.issue(line, SEVERITY_ERROR, "too_many_teams", text, limit=MAX_MATCHDAY_TEAMS)
            return
        team = ParsedTeam(line=line, name=name)
        keys: set[str] = set()
        for raw in split_names(body, self.known):
            player = self.canonical_player(raw)
            key = normalize(player)
            if not key:
                continue
            if len(player) > MAX_NAME_LENGTH:
                self.issue(line, SEVERITY_ERROR, "name_too_long", text,
                           team=name, limit=MAX_NAME_LENGTH)
                continue
            if key in self.team_of:
                self.issue(line, SEVERITY_ERROR, "player_in_two_teams", text,
                           player=player, team=self.team_of[key], other_team=name)
                continue
            if key in keys:
                self.issue(line, SEVERITY_WARNING, "duplicate_player", text,
                           player=player, team=name)
                continue
            if len(team.players) >= MAX_TEAM_PLAYERS:
                self.issue(line, SEVERITY_ERROR, "too_many_players", text,
                           team=name, limit=MAX_TEAM_PLAYERS)
                break
            if key not in self.known and key not in self.roster:
                self.new_players.append(player)
            self.roster[key] = player
            self.team_of[key] = name
            keys.add(key)
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
            self.issue(line, SEVERITY_ERROR, "unknown_team", text, team=missing.strip())
            return None
        if home_name == away_name:
            self.issue(line, SEVERITY_ERROR, "same_team_twice", text, team=home_name)
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
        for segment, annotation in split_annotations(text_body):
            for raw in split_names(segment, pool):
                bare = BARE_MULT_RE.match(raw.strip())
                if bare:
                    if entries:
                        entries[-1]["count"] = int(bare.group(1))
                    continue
                name_part, count = _strip_multiplier(raw)
                if not name_part:
                    continue
                entries.append({
                    "name": name_part, "count": count,
                    "own_goal": pending_own_goal, "assist": None,
                })
                pending_own_goal = False

            if annotation is None:
                continue
            marker = normalize(annotation)
            if marker in OWN_GOAL_WORDS:
                if entries:
                    entries[-1]["own_goal"] = True
                else:
                    pending_own_goal = True
            elif marker.isdigit():
                if not GOAL_COUNT_RE.fullmatch(marker):
                    self.issue(line, SEVERITY_ERROR, "bad_goal_count", text,
                               value=annotation.strip())
                elif entries:
                    entries[-1]["count"] = int(marker)
            elif marker and entries:
                entries[-1]["assist"] = annotation.strip()
            elif marker:
                self.issue(line, SEVERITY_WARNING, "stray_assist", text,
                           value=annotation.strip())

        for entry in entries:
            name_part = entry["name"]
            key = normalize(name_part)
            resolved = pool.get(key)
            if resolved is None:
                resolved = self.roster.get(key)
                if resolved is None:
                    self.issue(line, SEVERITY_WARNING, "unknown_scorer", text, player=name_part)
                    continue
                self.issue(line, SEVERITY_WARNING, "scorer_off_match", text,
                           player=resolved, home=match.home_team, away=match.away_team,
                           team=self.team_of.get(key, "?"))
            scorer_team = self.team_of.get(normalize(resolved), match.home_team)
            if entry["own_goal"]:
                credited = match.away_team if scorer_team == match.home_team else match.home_team
            else:
                credited = scorer_team

            assist = self.resolve_assist(line, entry, resolved, scorer_team, pool, text)
            if len(match.goals) + entry["count"] > match.home_score + match.away_score:
                self.issue(line, SEVERITY_ERROR, "too_many_goals", text,
                           **_score_params(match))
                return
            for _ in range(entry["count"]):
                match.goals.append(ParsedGoal(player=resolved, team=credited,
                                              own_goal=entry["own_goal"], assist=assist))

    def resolve_assist(self, line: int, entry: dict, scorer: str, scorer_team: str,
                       pool: dict[str, str], text: str) -> str | None:
        raw = entry["assist"]
        if raw is None:
            return None
        if entry["own_goal"]:
            self.issue(line, SEVERITY_WARNING, "own_goal_assist", text,
                       player=scorer, assist=raw)
            return None
        key = normalize(raw)
        resolved = pool.get(key) or self.roster.get(key)
        if resolved is None:
            self.issue(line, SEVERITY_WARNING, "unknown_assist", text, player=raw)
            return None
        if normalize(resolved) == normalize(scorer):
            self.issue(line, SEVERITY_WARNING, "self_assist", text, player=scorer)
            return None
        assist_team = self.team_of.get(normalize(resolved))
        if assist_team != scorer_team:
            self.issue(line, SEVERITY_WARNING, "assist_other_team", text,
                       assist=resolved, player=scorer)
            return None
        return resolved

    def finish(self) -> ParsedMatchday:
        if self.day.date is None:
            self.issue(self.day.line, SEVERITY_ERROR, "missing_date")
        if not self.day.teams:
            self.issue(self.day.line, SEVERITY_ERROR, "no_teams")
        if len(self.day.notes) > MAX_NOTES_LENGTH:
            self.issue(self.day.line, SEVERITY_ERROR, "notes_too_long", limit=MAX_NOTES_LENGTH)
        for match in self.day.matches:
            scored = {match.home_team: 0, match.away_team: 0}
            for goal in match.goals:
                if goal.team in scored:
                    scored[goal.team] += 1
            expected = match.home_score + match.away_score
            if match.goals and len(match.goals) != expected:
                self.issue(match.line, SEVERITY_WARNING, "goal_count_mismatch",
                           **_score_params(match), expected=expected, scored=len(match.goals))
            elif match.goals and (scored[match.home_team] != match.home_score
                                  or scored[match.away_team] != match.away_score):
                self.issue(match.line, SEVERITY_WARNING, "goal_side_mismatch",
                           **_score_params(match), home_scored=scored[match.home_team],
                           away_scored=scored[match.away_team])
        if self.day.mvp:
            self.day.mvp = self.canonical_player(self.day.mvp)
            key = normalize(self.day.mvp)
            if key not in self.team_of:
                self.issue(self.day.line, SEVERITY_WARNING, "mvp_not_playing",
                           player=self.day.mvp)
        return self.day


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
        line = WHITESPACE_RE.sub(" ", raw_line).strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if SEPARATOR_RE.match(line):
            close()
            continue

        venue_match = VENUE_SPLIT_RE.search(line)
        date_part = line[: venue_match.start()] if venue_match else line
        tokens = date_part.split()
        as_date = parse_date_token(tokens[0], year_hint) if tokens else None
        if as_date is not None and ":" not in date_part:
            close()
            builder = _MatchdayBuilder(index, known)
            builder.day.date = as_date
            builder.day.raw_date = date_part.strip()
            if venue_match:
                builder.set_venue(index, venue_match.group("venue").strip(), line)
            continue

        head, sep, tail = line.partition(":")
        head_key = normalize(head)

        if sep and head_key in RESERVED:
            if builder is None:
                builder = _MatchdayBuilder(index, known)
            value = tail.strip()
            if head_key in RESERVED_VENUE:
                builder.set_venue(index, value, line)
            elif head_key in RESERVED_MVP:
                builder.day.mvp = value or None
            elif head_key in RESERVED_DATE:
                parsed = parse_date_token(value, year_hint)
                if parsed is None:
                    builder.issue(index, SEVERITY_ERROR, "bad_date", line, value=value)
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
            result.issues.append(ParseIssue(index, SEVERITY_ERROR, "outside_matchday", line))
        else:
            builder.issue(index, SEVERITY_ERROR, "unexpected_line", line)

    close()

    if not result.matchdays:
        result.issues.append(ParseIssue(0, SEVERITY_ERROR, "empty"))
    result.issues.sort(key=lambda i: (i.line, i.severity))
    if len(result.issues) > MAX_ISSUES:
        dropped = result.issues[MAX_ISSUES:]
        del result.issues[MAX_ISSUES:]
        severity = (SEVERITY_ERROR if any(i.severity == SEVERITY_ERROR for i in dropped)
                    else SEVERITY_WARNING)
        result.issues.append(ParseIssue(dropped[0].line, severity, "too_many_issues",
                                        params={"count": len(dropped)}))
    return result

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app import models, parser, schemas, writes  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.security import hash_password  # noqa: E402

OWNER_USERNAME = "vini"
OWNER_PASSWORD = "pelada123"
GROUP_NAME = "Pelada da Quinta"
GROUP_DESCRIPTION = "Toda quinta, 19h, campo do Ze"
VISIBILITY = "public"
WEEKS = 24
LAST_GENERATED_DATE = date(2026, 9, 9)
VENUES = ["Campo do Ze", "Society da Vila"]
TEAM_NAMES = ["BRANCO", "VERMELHO", "AZUL"]
MATCHES_PER_DAY = 9
ATTENDANCE = 0.86
BASE_GOALS = 0.35
SKILL_WEIGHT = 0.30
SEED = 20260916
OWN_GOAL_CHANCE = 0.05
MISSING_SCORER_CHANCE = 0.06
ASSIST_CHANCE = 0.58
TRACK_ASSISTS = True
TEXT_OUTPUT = "peladas-demo.txt"
APPLY = True

ROSTER = [
    ("golin", 0.90, 0.95), ("galetti", 0.62, 0.30), ("galo", 0.70, 0.62),
    ("rick", 0.55, 0.22), ("palma", 0.48, 0.18), ("disciplina", 0.66, 0.40),
    ("mini", 0.44, 0.26), ("vini", 0.72, 0.58), ("bamma", 0.58, 0.34),
    ("breno", 0.50, 0.20), ("igor", 0.64, 0.44), ("rod kauer", 0.68, 0.36),
    ("cesar", 0.46, 0.16), ("beat", 0.52, 0.28), ("ney", 0.60, 0.48),
    ("rod", 0.74, 0.52), ("lusca", 0.42, 0.14), ("pipi", 0.56, 0.38),
    ("nona", 0.38, 0.12), ("cop", 0.50, 0.24), ("guarino", 0.64, 0.30),
]

REAL_MATCHDAY = """16/09/2026 @ Campo do Ze

BRANCO: golin, galetti, galo, rick, palma, disciplina, mini
VERMELHO: vini, bamma, breno, igor, rod kauer, cesar, beat
AZUL: ney, rod, lusca, pipi, nona, cop, guarino

VERMELHO 0x0 AZUL
BRANCO 0x0 AZUL
BRANCO 1x0 VERMELHO: golin (galetti)
BRANCO 2x0 AZUL: golin, galo (golin)
BRANCO 0x0 VERMELHO
VERMELHO 0x0 AZUL
AZUL 0x1 BRANCO: disciplina (mini)
BRANCO 1x1 VERMELHO: golin (galetti), vini

MVP: golin"""

SKILL = {name: skill for name, skill, _ in ROSTER}
ATTACK = {name: attack for name, _, attack in ROSTER}
PASSING = {name: max(0.08, skill - attack * 0.55) for name, skill, attack in ROSTER}


def draft(rng: random.Random, attendees: list[str]) -> list[list[str]]:
    ranked = sorted(attendees, key=lambda n: SKILL[n] + rng.uniform(-0.12, 0.12), reverse=True)
    teams: list[list[str]] = [[], [], []]
    for index, name in enumerate(ranked):
        order = index // 3
        slot = index % 3 if order % 2 == 0 else 2 - (index % 3)
        teams[slot].append(name)
    return teams


def team_strength(team: list[str]) -> float:
    return sum(SKILL[name] for name in team) / len(team) if team else 0.0


def sample_goals(rng: random.Random, rate: float) -> int:
    goals = 0
    while goals < 5 and rng.random() < rate / (goals + 1):
        goals += 1
    return goals


def pick_scorers(rng: random.Random, team: list[str], count: int) -> list[str]:
    if count == 0:
        return []
    weights = [ATTACK[name] + 0.05 for name in team]
    return rng.choices(team, weights=weights, k=count)


def pick_assist(rng: random.Random, team: list[str], scorer: str) -> str | None:
    if not TRACK_ASSISTS or rng.random() > ASSIST_CHANCE:
        return None
    options = [name for name in team if name != scorer]
    if not options:
        return None
    weights = [PASSING[name] + 0.05 for name in options]
    return rng.choices(options, weights=weights, k=1)[0]


def build_matchday(rng: random.Random, day: date) -> str:
    attendees = [name for name, _, _ in ROSTER if rng.random() < ATTENDANCE]
    while len(attendees) < 18:
        missing = [name for name, _, _ in ROSTER if name not in attendees]
        attendees.append(rng.choice(missing))
    teams = draft(rng, attendees)

    header = f"{day.strftime('%d/%m/%Y')} @ {rng.choice(VENUES)}"
    lines = [header, ""]
    for name, members in zip(TEAM_NAMES, teams):
        lines.append(f"{name}: {', '.join(members)}")
    lines.append("")

    pairs = [(0, 1), (1, 2), (2, 0)]
    scorers_count: dict[str, int] = {}
    day_points: dict[int, int] = {0: 0, 1: 0, 2: 0}

    for index in range(MATCHES_PER_DAY):
        home_index, away_index = pairs[index % 3]
        if index % 2 == 1:
            home_index, away_index = away_index, home_index
        home, away = teams[home_index], teams[away_index]
        edge = (team_strength(home) - team_strength(away)) * SKILL_WEIGHT
        home_goals = sample_goals(rng, max(0.05, BASE_GOALS + edge))
        away_goals = sample_goals(rng, max(0.05, BASE_GOALS - edge))

        if home_goals > away_goals:
            day_points[home_index] += 3
        elif home_goals < away_goals:
            day_points[away_index] += 3
        else:
            day_points[home_index] += 1
            day_points[away_index] += 1

        scoreline = f"{TEAM_NAMES[home_index]} {home_goals}x{away_goals} {TEAM_NAMES[away_index]}"

        credited: list[tuple[str, int]] = []
        for scorer in pick_scorers(rng, home, home_goals):
            credited.append((scorer, home_index))
            scorers_count[scorer] = scorers_count.get(scorer, 0) + 1
        for scorer in pick_scorers(rng, away, away_goals):
            credited.append((scorer, away_index))
            scorers_count[scorer] = scorers_count.get(scorer, 0) + 1

        goal_line: list[str] = []
        for position, (scorer, side) in enumerate(credited):
            last = position == len(credited) - 1
            if last and rng.random() < OWN_GOAL_CHANCE:
                conceding = away_index if side == home_index else home_index
                own_scorer = rng.choice(teams[conceding])
                scorers_count[scorer] = scorers_count.get(scorer, 1) - 1
                goal_line.append(f"{own_scorer} (gc)")
                continue
            assist = pick_assist(rng, teams[side], scorer)
            goal_line.append(f"{scorer} ({assist})" if assist else scorer)

        if goal_line and len(goal_line) > 1 and rng.random() < MISSING_SCORER_CHANCE:
            dropped = goal_line.pop(rng.randrange(len(goal_line)))
            base = dropped.split(" (")[0]
            if not dropped.endswith("(gc)"):
                scorers_count[base] = scorers_count.get(base, 1) - 1

        lines.append(f"{scoreline}: {', '.join(goal_line)}" if goal_line else scoreline)

    champion = max(day_points, key=lambda k: day_points[k])
    candidates = list(teams[champion])
    scored = {name: count for name, count in scorers_count.items() if count > 0}
    if scored:
        top = max(scored, key=lambda k: scored[k])
        candidates += [top, top]
    lines.append("")
    lines.append(f"MVP: {rng.choice(candidates)}")
    return "\n".join(lines)


def build_season() -> str:
    rng = random.Random(SEED)
    blocks = []
    for week in range(WEEKS, 0, -1):
        blocks.append(build_matchday(rng, LAST_GENERATED_DATE - timedelta(weeks=week - 1)))
    blocks.append(REAL_MATCHDAY)
    return "\n\n---\n\n".join(blocks) + "\n"


def main() -> None:
    text = build_season()
    Path(TEXT_OUTPUT).write_text(text, encoding="utf-8")
    print(f"texto gerado em {TEXT_OUTPUT} ({len(text.splitlines())} linhas)")

    result = parser.parse(text)
    errors = [i for i in result.issues if i.severity == "error"]
    warnings = [i for i in result.issues if i.severity == "warning"]
    print(f"parser: {len(result.matchdays)} dias, {len(errors)} erros, {len(warnings)} avisos")
    for issue in errors[:10]:
        print(f"  [erro] linha {issue.line}: {issue.message}")
    if errors:
        sys.exit("texto gerado tem erros")
    if not APPLY:
        print("APPLY = False — nada gravado.")
        return

    init_db()
    with Session(engine) as db:
        owner = db.exec(select(models.User).where(models.User.username == OWNER_USERNAME)).first()
        if owner is None:
            owner = models.User(
                username=OWNER_USERNAME, password_hash=hash_password(OWNER_PASSWORD)
            )
            db.add(owner)
            db.flush()

        group = db.exec(select(models.Group).where(models.Group.name == GROUP_NAME)).first()
        if group is None:
            from app.services import unique_slug

            group = models.Group(
                name=GROUP_NAME,
                slug=unique_slug(db, GROUP_NAME),
                description=GROUP_DESCRIPTION,
                visibility=VISIBILITY,
                track_assists=TRACK_ASSISTS,
            )
            db.add(group)
            db.flush()
            db.add(models.GroupOwner(group_id=group.id, user_id=owner.id))
            db.flush()

        players: dict[str, models.Player] = {
            parser.normalize(p.name): p
            for p in db.exec(
                select(models.Player).where(models.Player.group_id == group.id)
            ).all()
        }
        for name in result.new_players:
            key = parser.normalize(name)
            if key in players:
                continue
            player = models.Player(group_id=group.id, name=name)
            db.add(player)
            db.flush()
            players[key] = player

        venues: dict[str, models.Venue] = {}
        written = 0
        for day in result.matchdays:
            venue_id = None
            if day.venue:
                key = parser.normalize(day.venue)
                venue = venues.get(key) or db.exec(
                    select(models.Venue).where(
                        models.Venue.group_id == group.id, models.Venue.name == day.venue
                    )
                ).first()
                if venue is None:
                    venue = models.Venue(group_id=group.id, name=day.venue)
                    db.add(venue)
                    db.flush()
                venues[key] = venue
                venue_id = venue.id

            mvp = players.get(parser.normalize(day.mvp)) if day.mvp else None
            team_index = {team.name: index for index, team in enumerate(day.teams)}
            payload = schemas.MatchdayCreate(
                date=day.date,
                venue_id=venue_id,
                mvp_player_id=mvp.id if mvp else None,
                notes=day.notes,
                teams=[
                    schemas.TeamIn(
                        name=team.name,
                        player_ids=[players[parser.normalize(n)].id for n in team.players],
                    )
                    for team in day.teams
                ],
                matches=[
                    schemas.MatchIn(
                        home_team_index=team_index[match.home_team],
                        away_team_index=team_index[match.away_team],
                        home_score=match.home_score,
                        away_score=match.away_score,
                        goals=[
                            schemas.GoalIn(
                                player_id=players[parser.normalize(g.player)].id,
                                own_goal=g.own_goal,
                                assist_player_id=(
                                    players[parser.normalize(g.assist)].id if g.assist else None
                                ),
                            )
                            for g in match.goals
                        ],
                    )
                    for match in day.matches
                ],
            )
            writes.validate_payload(db, group.id, payload)
            writes.apply_payload(db, models.Matchday(group_id=group.id, date=day.date), payload)
            written += 1

        db.commit()
        print(f"{written} dias gravados em '{group.name}' (slug: {group.slug})")
        print(f"login: {OWNER_USERNAME} / {OWNER_PASSWORD}")


if __name__ == "__main__":
    main()
